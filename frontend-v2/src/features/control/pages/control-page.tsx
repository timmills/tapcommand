import { useEffect, useMemo, useState, useRef } from 'react';
import { useNavigate } from 'react-router-dom';
import { useManagedDevices } from '@/features/devices/hooks/use-managed-devices';
import { useDeviceTags } from '@/features/settings/hooks/use-device-tags';
import { useAvailableChannels } from '@/features/devices/hooks/use-available-channels';
import { usePortStatus, getLastChannelForPort, getPowerStateForPort } from '@/features/devices/hooks/use-port-status';
import { useQueueMetrics } from '@/features/devices/hooks/use-queue-metrics';
import { sendDiagnosticSignal, sendBulkCommand } from '@/features/devices/api/devices-api';
import type { ChannelOption, DeviceTag, ManagedDevice } from '@/types';
import { formatRelativeTime } from '@/utils/datetime';
import { ChannelSelectorModal } from '../components/channel-selector-modal';
import { useVirtualDevices } from '@/features/devices/hooks/use-virtual-devices';

interface PortRow {
  id: string;
  portId: number;
  controllerId: number;
  controllerName: string;
  hostname: string;
  portNumber: number;
  deviceName: string;
  location: string;
  tags: DeviceTag[];
  lastSeen: string;
  isOnline: boolean;
  defaultChannel: string | null;
}

export const ControlPage = () => {
  const navigate = useNavigate();
  const { data: controllers = [], isLoading, error, isError } = useManagedDevices();
  const { data: tags = [] } = useDeviceTags();
  const { data: channels = [] } = useAvailableChannels();
  const { data: queueMetrics } = useQueueMetrics();
  const { data: virtualDevices = [] } = useVirtualDevices();

  const rows = useMemo(() => {
    console.log('[ControlPage] Building rows from controllers:', {
      controllerCount: controllers.length,
      virtualDeviceCount: virtualDevices.length,
      controllers: controllers.map(c => ({
        id: c.id,
        hostname: c.hostname,
        portCount: c.ir_ports?.length,
        ports: c.ir_ports?.map(p => ({ port: p.port_number, active: p.is_active }))
      }))
    });
    const result = buildRows(controllers, tags, virtualDevices);
    console.log('[ControlPage] Built rows:', result.length);
    return result;
  }, [controllers, tags, virtualDevices]);

  const [selectedIds, setSelectedIds] = useState<Set<string>>(new Set());
  const [nameFilter, setNameFilter] = useState('');
  const [locationFilter, setLocationFilter] = useState<string | null>(null);
  const [collapsedLocations, setCollapsedLocations] = useState<Set<string>>(new Set());
  const [showChannelModal, setShowChannelModal] = useState(false);

  // Secret exit mechanism
  const [holdProgress, setHoldProgress] = useState(0);
  const holdTimerRef = useRef<number | null>(null);
  const holdStartRef = useRef<number>(0);

  const handlePressStart = (e: React.MouseEvent | React.TouchEvent) => {
    e.preventDefault(); // Prevent default touch behavior
    holdStartRef.current = Date.now();
    setHoldProgress(0);

    holdTimerRef.current = window.setInterval(() => {
      const elapsed = Date.now() - holdStartRef.current;
      const progress = Math.min((elapsed / 5000) * 100, 100);
      setHoldProgress(progress);

      if (progress >= 100) {
        if (holdTimerRef.current) clearInterval(holdTimerRef.current);
        navigate('/controllers');
      }
    }, 50);
  };

  const handlePressEnd = (e: React.MouseEvent | React.TouchEvent) => {
    e.preventDefault();
    if (holdTimerRef.current) {
      clearInterval(holdTimerRef.current);
      holdTimerRef.current = null;
    }
    setHoldProgress(0);
  };

  const displayRows = useMemo(() => {
    const lowered = nameFilter.trim().toLowerCase();
    return rows.filter((row) => {
      if (lowered && !row.deviceName.toLowerCase().includes(lowered)) {
        return false;
      }
      if (locationFilter && row.location !== locationFilter) {
        return false;
      }
      return true;
    });
  }, [rows, nameFilter, locationFilter]);

  useEffect(() => {
    const validIds = new Set(displayRows.map((row) => row.id));
    setSelectedIds((prev) => {
      const filtered = [...prev].filter((id) => validIds.has(id));
      // Only update if something actually changed to avoid infinite loops
      if (filtered.length !== prev.size) {
        return new Set(filtered);
      }
      return prev;
    });
  }, [displayRows]);

  const toggleSelection = (id: string) => {
    setSelectedIds((prev) => {
      const next = new Set(prev);
      if (next.has(id)) {
        next.delete(id);
      } else {
        next.add(id);
      }
      return next;
    });
  };

  const toggleAll = () => {
    const currentIds = displayRows.map((row) => row.id);
    const allSelected = currentIds.every((id) => selectedIds.has(id));
    setSelectedIds(allSelected ? new Set() : new Set(currentIds));
  };

  const quickSelectTag = (tagId: number) => {
    const matchingIds = rows.filter((row) => row.tags.some((tag) => tag.id === tagId)).map((row) => row.id);
    const allSelected = matchingIds.every((id) => selectedIds.has(id));
    setSelectedIds((prev) => {
      if (allSelected) {
        const next = new Set(prev);
        matchingIds.forEach((id) => next.delete(id));
        return next;
      }
      return new Set(matchingIds);
    });
  };

  const quickSelectLocation = (location: string) => {
    const matchingIds = rows.filter((row) => row.location === location).map((row) => row.id);
    const allSelected = matchingIds.every((id) => selectedIds.has(id));
    setSelectedIds((prev) => {
      if (allSelected) {
        const next = new Set(prev);
        matchingIds.forEach((id) => next.delete(id));
        return next;
      }
      return new Set(matchingIds);
    });
    setLocationFilter(location);
  };

  const selectedCount = selectedIds.size;
  const selectedRows = useMemo(() => rows.filter((row) => selectedIds.has(row.id)), [rows, selectedIds]);

  // Group rows by location
  const rowsByLocation = useMemo(() => {
    const groups = new Map<string, PortRow[]>();
    displayRows.forEach((row) => {
      const location = row.location || 'Unassigned';
      if (!groups.has(location)) {
        groups.set(location, []);
      }
      groups.get(location)!.push(row);
    });
    return groups;
  }, [displayRows]);

  const toggleLocation = (location: string) => {
    setCollapsedLocations((prev) => {
      const next = new Set(prev);
      if (next.has(location)) {
        next.delete(location);
      } else {
        next.add(location);
      }
      return next;
    });
  };

  const selectAllInLocation = (location: string) => {
    const locationRows = rowsByLocation.get(location) || [];
    const locationIds = locationRows.map((row) => row.id);
    const allSelected = locationIds.every((id) => selectedIds.has(id));

    setSelectedIds((prev) => {
      const next = new Set(prev);
      if (allSelected) {
        locationIds.forEach((id) => next.delete(id));
      } else {
        locationIds.forEach((id) => next.add(id));
      }
      return next;
    });
  };

  return (
    <>
      <div className="space-y-6 pr-56">
        {queueMetrics && (queueMetrics.pending > 0 || queueMetrics.processing > 0 || queueMetrics.failed > 0) && (
          <QueueStatusBar metrics={queueMetrics} />
        )}

        <section className="relative">
          <h2
            className="relative inline-block cursor-pointer select-none text-xl font-semibold text-slate-50 touch-none"
            onMouseDown={handlePressStart}
            onMouseUp={handlePressEnd}
            onMouseLeave={handlePressEnd}
            onTouchStart={handlePressStart}
            onTouchEnd={handlePressEnd}
            onTouchCancel={handlePressEnd}
            onContextMenu={(e) => e.preventDefault()}
          >
            TapCommand
            {holdProgress > 0 && (
              <div
                className="absolute bottom-0 left-0 h-0.5 bg-slate-400 transition-all"
                style={{ width: `${holdProgress}%` }}
              />
            )}
          </h2>
        </section>

        <section className="space-y-4">
          {isLoading ? (
            <div className="rounded-xl border border-slate-200 bg-white p-6 text-center text-slate-500 shadow-sm">
              Loading controllers…
            </div>
          ) : isError ? (
            <div className="rounded-xl border border-red-200 bg-red-50 p-6 text-center shadow-sm">
              <div className="text-red-700 font-semibold mb-2">Error loading controllers</div>
              <div className="text-sm text-red-600">{error?.message || 'Unknown error'}</div>
              <div className="text-xs text-slate-500 mt-2">Check console for details</div>
            </div>
          ) : displayRows.length === 0 ? (
            <div className="rounded-xl border border-slate-200 bg-white p-6 text-center text-slate-500 shadow-sm">
              <div className="font-semibold mb-2">No devices match the current filters</div>
              <div className="text-sm">
                Controllers: {controllers.length} | Rows built: {rows.length} | Displayed: {displayRows.length}
              </div>
              <div className="text-xs mt-2">
                {controllers.length === 0 && "No controllers loaded from API"}
                {controllers.length > 0 && rows.length === 0 && "All ports filtered out (check port.is_active)"}
                {rows.length > 0 && displayRows.length === 0 && "All rows filtered out (check filters)"}
              </div>
            </div>
          ) : (
            <div className="space-y-4">
              {Array.from(rowsByLocation.entries())
                .sort(([a], [b]) => a.localeCompare(b))
                .map(([location, locationRows]) => {
                  const isCollapsed = collapsedLocations.has(location);
                  const onlineCount = locationRows.filter((r) => r.isOnline).length;
                  const selectedInLocation = locationRows.filter((r) => selectedIds.has(r.id)).length;

                  return (
                    <div key={location} className="rounded-xl border border-slate-700 bg-slate-800 shadow-sm">
                      <div className="flex items-center justify-between px-6 py-4">
                        <button
                          type="button"
                          onClick={() => toggleLocation(location)}
                          className="flex flex-1 items-center gap-3 text-left transition"
                        >
                          <svg
                            className={`h-5 w-5 text-slate-400 transition-transform ${isCollapsed ? '' : 'rotate-90'}`}
                            fill="none"
                            stroke="currentColor"
                            viewBox="0 0 24 24"
                          >
                            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 5l7 7-7 7" />
                          </svg>
                          <h3 className="text-lg font-semibold text-slate-100">{location}</h3>
                          <span className="text-sm text-slate-400">
                            {locationRows.length} device{locationRows.length === 1 ? '' : 's'}
                          </span>
                          <span className="text-sm text-slate-400">
                            • {onlineCount} online
                          </span>
                          {selectedInLocation > 0 && (
                            <span className="rounded-full bg-brand-100 px-2 py-1 text-xs font-medium text-brand-700">
                              {selectedInLocation} selected
                            </span>
                          )}
                        </button>
                        <div className="flex items-center gap-2">
                          <button
                            type="button"
                            onClick={async (e) => {
                              e.stopPropagation();
                              // Use selected rows if any in this location, otherwise all rows
                              const rowsToControl = selectedInLocation > 0
                                ? locationRows.filter((r) => selectedIds.has(r.id))
                                : locationRows;
                              const targets = rowsToControl.map((row) => ({
                                hostname: row.hostname,
                                port: row.portNumber,
                              }));
                              await sendBulkCommand({ targets, command: 'power_on', priority: 5 });
                            }}
                            className="min-h-[36px] rounded-md border border-green-700 bg-green-900/30 px-3 py-1.5 text-xs font-medium text-green-400 transition hover:bg-green-900/50"
                          >
                            Power On
                          </button>
                          <button
                            type="button"
                            onClick={async (e) => {
                              e.stopPropagation();
                              // Use selected rows if any in this location, otherwise all rows
                              const rowsToControl = selectedInLocation > 0
                                ? locationRows.filter((r) => selectedIds.has(r.id))
                                : locationRows;
                              const targets = rowsToControl.map((row) => ({
                                hostname: row.hostname,
                                port: row.portNumber,
                              }));
                              await sendBulkCommand({ targets, command: 'power_off', priority: 5 });
                            }}
                            className="min-h-[36px] rounded-md border border-red-700 bg-red-900/30 px-3 py-1.5 text-xs font-medium text-red-400 transition hover:bg-red-900/50"
                          >
                            Power Off
                          </button>
                          <button
                            type="button"
                            onClick={(e) => {
                              e.stopPropagation();
                              selectAllInLocation(location);
                            }}
                            className="min-h-[36px] rounded-md border border-slate-600 bg-slate-700 px-3 py-1.5 text-xs font-medium text-slate-300 transition hover:bg-slate-600 hover:text-brand-400"
                          >
                            Select All
                          </button>
                        </div>
                      </div>

                      {!isCollapsed && (
                        <div className="border-t border-slate-700 p-4">
                          <div className="grid gap-3 md:grid-cols-2 xl:grid-cols-3">
                            {locationRows.map((row) => (
                              <ControlCard
                                key={row.id}
                                row={row}
                                channels={channels}
                                selected={selectedIds.has(row.id)}
                                onToggle={() => toggleSelection(row.id)}
                                onTagSelect={(tagId) => quickSelectTag(tagId)}
                                onLocationSelect={(location) => quickSelectLocation(location)}
                              />
                            ))}
                          </div>
                        </div>
                      )}
                    </div>
                  );
                })}
            </div>
          )}
        </section>
      </div>

      <ActionToolbar
        selectedRows={selectedRows}
        totalRows={displayRows.length}
        onOpenChannelModal={() => setShowChannelModal(true)}
        toggleAll={toggleAll}
        nameFilter={nameFilter}
        onNameFilterChange={setNameFilter}
      />

      <ChannelSelectorModal
        isOpen={showChannelModal}
        onClose={() => setShowChannelModal(false)}
        channels={channels}
        controllers={controllers}
        selectedDeviceCount={selectedCount}
        onSelectChannel={async (channelLcn) => {
          // Send bulk channel change command
          try {
            const targets = selectedRows.map((row) => ({
              hostname: row.hostname,
              port: row.portNumber,
            }));

            await sendBulkCommand({
              targets,
              command: 'channel',
              channel: channelLcn,
              priority: 5,
            });

            console.log(`Channel changed to ${channelLcn} for ${targets.length} devices`);
          } catch (error) {
            console.error('Failed to change channel:', error);
          }
        }}
      />
    </>
  );
};

const ControlCard = ({
  row,
  channels,
  selected,
  onToggle,
  onTagSelect,
  onLocationSelect: _onLocationSelect,
}: {
  row: PortRow;
  channels: ChannelOption[];
  selected: boolean;
  onToggle: () => void;
  onTagSelect: (tagId: number) => void;
  onLocationSelect: (location: string) => void;
}) => {
  // Fetch port status for this device
  const { data: portStatus } = usePortStatus(row.hostname);
  const lastChannel = getLastChannelForPort(portStatus, row.portNumber);
  const powerState = getPowerStateForPort(portStatus, row.portNumber);

  // Look up channel name from LCN
  const channelInfo = useMemo(() => {
    if (!lastChannel) return null;

    // Find channel by LCN or Foxtel number
    const channel = channels.find(
      (ch) => ch.lcn === lastChannel || ch.foxtel_number === lastChannel
    );

    if (!channel) return { lcn: lastChannel, name: null };

    // Truncate long channel names (max 12 chars, add ellipsis)
    const displayName = channel.channel_name.length > 12
      ? channel.channel_name.substring(0, 12) + '...'
      : channel.channel_name;

    return { lcn: lastChannel, name: displayName };
  }, [lastChannel, channels]);

  return (
    <button
      type="button"
      onClick={onToggle}
      className={`flex w-full gap-3 rounded-2xl border-2 px-4 py-4 text-left shadow-lg transition active:scale-[0.98] ${
        selected
          ? 'border-brand-500 bg-brand-900 ring-2 ring-brand-700'
          : 'border-slate-700 bg-slate-800 hover:border-brand-700 hover:shadow-xl'
      }`}
    >
      {/* Main content area */}
      <div className="flex-1">
        {/* Header with power state and channel */}
        <div className="flex items-start justify-between gap-3">
          <div className="flex items-center gap-2">
            {/* Power State Indicator - larger and more prominent */}
            {powerState && (
              <div
                className={`h-3.5 w-3.5 rounded-full ${
                  powerState === 'on' ? 'bg-green-500 shadow-green-500/50 shadow-md' : 'bg-red-500 shadow-red-500/50 shadow-md'
                }`}
                title={`Power: ${powerState}`}
              />
            )}
            <h3 className="text-xl font-semibold text-slate-100">{row.deviceName}</h3>
          </div>
          {channelInfo && (
            <span
              className="rounded-lg bg-brand-600 px-3 py-1.5 text-sm font-semibold text-white"
              title={channelInfo.name ? `${channelInfo.lcn} - ${channelInfo.name}` : channelInfo.lcn}
            >
              {channelInfo.name || `CH ${channelInfo.lcn}`}
            </span>
          )}
        </div>

        {/* Status info */}
        <div className="mt-2 flex flex-wrap items-center gap-2 text-xs text-slate-400">
          <span className={`font-medium ${row.isOnline ? 'text-green-400' : 'text-slate-500'}`}>
            {row.isOnline ? '● Online' : '○ Offline'}
          </span>
          <span>•</span>
          <span>Updated {formatRelativeTime(row.lastSeen)}</span>
          {!channelInfo && (
            <>
              <span>•</span>
              <span className="text-slate-500">No channel history</span>
            </>
          )}
        </div>

        {/* Selected indicator */}
        {selected && (
          <div className="mt-3 flex items-center gap-2 text-sm font-semibold text-brand-400">
            <svg className="h-5 w-5" fill="currentColor" viewBox="0 0 20 20">
              <path fillRule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zm3.707-9.293a1 1 0 00-1.414-1.414L9 10.586 7.707 9.293a1 1 0 00-1.414 1.414l2 2a1 1 0 001.414 0l4-4z" clipRule="evenodd" />
            </svg>
            Selected
          </div>
        )}
      </div>

      {/* Tags sidebar on right */}
      {row.tags.length > 0 && (
        <div className="flex flex-col gap-2" onClick={(e) => e.stopPropagation()}>
          {row.tags.map((tag) => (
            <button
              key={tag.id}
              type="button"
              onClick={(e) => {
                e.stopPropagation();
                onTagSelect(tag.id);
              }}
              className="min-h-[36px] rounded-lg border-2 px-3 py-1.5 text-xs font-semibold transition hover:brightness-95 active:scale-95"
              style={{
                borderColor: tag.color || '#cbd5e1',
                backgroundColor: tag.color ? `${tag.color}15` : '#f1f5f9',
                color: tag.color || '#475569'
              }}
            >
              {tag.name}
            </button>
          ))}
        </div>
      )}
    </button>
  );
};

const ActionToolbar = ({
  selectedRows,
  totalRows,
  onOpenChannelModal,
  toggleAll,
  nameFilter,
  onNameFilterChange,
}: {
  selectedRows: PortRow[];
  totalRows: number;
  onOpenChannelModal: () => void;
  toggleAll: () => void;
  nameFilter: string;
  onNameFilterChange: (value: string) => void;
}) => {
  const count = selectedRows.length;
  const [isProcessing, setIsProcessing] = useState(false);

  const sendBulkAction = async (command: string) => {
    if (count === 0 || isProcessing) return;

    setIsProcessing(true);
    try {
      const targets = selectedRows.map(row => ({
        hostname: row.hostname,
        port: row.portNumber
      }));

      const response = await sendBulkCommand({
        targets,
        command,
        priority: 5
      });

      console.log(`Queued ${response.queued_count} commands (batch ${response.batch_id})`);
    } catch (error) {
      console.error('Failed to send bulk command:', error);
    } finally {
      setIsProcessing(false);
    }
  };

  const handleDefaultChannel = async () => {
    if (count === 0 || isProcessing) return;

    setIsProcessing(true);
    try {
      // Group by channel to optimize bulk commands
      const channelGroups = new Map<string, typeof selectedRows>();

      selectedRows.forEach(row => {
        if (row.defaultChannel) {
          const existing = channelGroups.get(row.defaultChannel) || [];
          existing.push(row);
          channelGroups.set(row.defaultChannel, existing);
        }
      });

      if (channelGroups.size === 0) {
        console.log('No devices with default channels configured');
        setIsProcessing(false);
        return;
      }

      // Send bulk commands for each channel group
      const responses = await Promise.all(
        Array.from(channelGroups.entries()).map(([channel, rows]) =>
          sendBulkCommand({
            targets: rows.map(row => ({ hostname: row.hostname, port: row.portNumber })),
            command: 'channel',
            channel,
            priority: 5
          })
        )
      );

      const totalQueued = responses.reduce((sum, r) => sum + r.queued_count, 0);
      console.log(`Queued default channel changes for ${totalQueued} devices`);
    } catch (error) {
      console.error('Failed to send default channel commands:', error);
    } finally {
      setIsProcessing(false);
    }
  };

  const handleIdentify = async () => {
    if (count === 0 || isProcessing) return;

    setIsProcessing(true);
    try {
      const uniqueHostnames = [...new Set(selectedRows.map(row => row.hostname))];
      await Promise.all(
        uniqueHostnames.map(hostname => sendDiagnosticSignal(hostname, 0, 1))
      );
    } catch (error) {
      console.error('Failed to send diagnostic signal:', error);
    } finally {
      setIsProcessing(false);
    }
  };

  const allSelected = totalRows > 0 && selectedRows.length === totalRows;

  return (
    <div className="fixed right-6 top-6 z-20 w-48 rounded-2xl border border-slate-700 bg-slate-800 shadow-xl">
      {/* Header with Select All */}
      <div className="border-b border-slate-700 px-4 py-3">
        <div className="flex items-center justify-between">
          <div>
            <div className="font-semibold text-slate-100">
              {count > 0 ? `${count} Selected` : 'Actions'}
            </div>
            <div className="text-xs text-slate-400">
              {count > 0 ? `${count} device${count === 1 ? '' : 's'}` : 'Select devices'}
            </div>
          </div>
          <label className="flex cursor-pointer items-center gap-2">
            <span className="text-xs font-medium text-slate-300">All</span>
            <input
              type="checkbox"
              checked={allSelected}
              onChange={toggleAll}
              className="h-4 w-4 rounded border-slate-600 bg-slate-700 text-brand-600 focus:ring-brand-500"
            />
          </label>
        </div>
      </div>

      {/* Actions */}
      <div className="flex flex-col gap-1 p-2">
        <div className="px-2 py-1 text-xs font-semibold uppercase tracking-wide text-slate-400">Power</div>
        <ActionButton
          label="Power On"
          onClick={() => sendBulkAction('power_on')}
          disabled={count === 0 || isProcessing}
        />
        <ActionButton
          label="Power Off"
          onClick={() => sendBulkAction('power_off')}
          disabled={count === 0 || isProcessing}
        />
        <ActionButton
          label="Power Toggle"
          onClick={() => sendBulkAction('power')}
          disabled={count === 0 || isProcessing}
        />

        <div className="mt-2 px-2 py-1 text-xs font-semibold uppercase tracking-wide text-slate-400">Channel</div>
        <ActionButton
          label="Select Channel"
          onClick={onOpenChannelModal}
          disabled={count === 0 || isProcessing}
        />
        <ActionButton
          label="Default Channel"
          onClick={handleDefaultChannel}
          disabled={count === 0 || isProcessing}
        />

        <div className="mt-2 px-2 py-1 text-xs font-semibold uppercase tracking-wide text-slate-400">Volume</div>
        <ActionButton
          label="Mute Toggle"
          onClick={() => sendBulkAction('mute')}
          disabled={count === 0 || isProcessing}
        />
        <ActionButton
          label="Volume +"
          onClick={() => sendBulkAction('volume_up')}
          disabled={count === 0 || isProcessing}
        />
        <ActionButton
          label="Volume –"
          onClick={() => sendBulkAction('volume_down')}
          disabled={count === 0 || isProcessing}
        />

        <div className="mt-2 border-t border-slate-700 pt-2">
          <ActionButton
            label={isProcessing ? "Processing..." : "Identify (ID)"}
            onClick={handleIdentify}
            disabled={count === 0 || isProcessing}
          />
        </div>
      </div>

      {/* Filter at bottom */}
      <div className="border-t border-slate-700 p-4">
        <label className="text-xs font-medium text-slate-300">
          Filter by name
          <input
            type="text"
            value={nameFilter}
            onChange={(e) => onNameFilterChange(e.target.value)}
            placeholder="Search devices…"
            className="mt-1.5 w-full rounded-lg border border-slate-600 bg-slate-700 px-3 py-2 text-sm text-slate-100 placeholder-slate-400 focus:border-brand-500 focus:outline-none focus:ring-1 focus:ring-brand-500"
          />
        </label>
      </div>
    </div>
  );
};

const ActionButton = ({
  label,
  onClick,
  disabled = false
}: {
  label: string;
  onClick?: () => void;
  disabled?: boolean;
}) => (
  <button
    type="button"
    onClick={onClick}
    disabled={disabled}
    className={`w-full rounded-lg border border-slate-600 bg-slate-700 px-4 py-2.5 text-left text-sm font-medium transition min-h-[44px] ${
      disabled
        ? 'text-slate-500 cursor-not-allowed'
        : 'text-slate-200 hover:border-brand-600 hover:bg-slate-600 hover:text-brand-400 active:scale-[0.98]'
    }`}
  >
    {label}
  </button>
);

interface VirtualDevice {
  id: number;
  controller_id: number;
  port_number: number;
  port_id: string | null;
  device_name: string;
  device_type: string | null;
  ip_address: string;
  mac_address: string | null;
  port: number | null;
  protocol: string | null;
  is_active: boolean;
  is_online: boolean;
  fallback_ir_controller: string | null;
  fallback_ir_port: number | null;
  power_on_method: string | null;
  control_strategy: string | null;
}

function buildRows(controllers: ManagedDevice[], tags: DeviceTag[], virtualDevices: VirtualDevice[]): PortRow[] {
  const tagMap = new Map<number, DeviceTag>(tags.map((tag) => [tag.id, tag]));

  const rows: PortRow[] = [];

  // Build set of IR ports that are used as hybrid fallbacks
  const hybridIRPorts = new Set<string>();
  virtualDevices.forEach((vd) => {
    if (vd.fallback_ir_controller && vd.fallback_ir_port) {
      hybridIRPorts.add(`${vd.fallback_ir_controller}:${vd.fallback_ir_port}`);
    }
  });

  // Add IR controller ports (excluding those used as hybrid fallbacks)
  controllers.forEach((controller) => {
    // Skip virtual controllers - they'll be added from virtualDevices
    if (controller.device_type === 'virtual_controller') {
      return;
    }

    controller.ir_ports.forEach((port) => {
      if (!port.is_active || port.port_number === 0) {
        return;
      }

      // Skip if this IR port is used as a hybrid fallback
      const portKey = `${controller.hostname}:${port.port_number}`;
      if (hybridIRPorts.has(portKey)) {
        console.log(`[buildRows] Skipping IR port ${portKey} - used as hybrid fallback`);
        return;
      }

      rows.push({
        id: `ir-${controller.id}-${port.port_number}`,
        portId: port.id ?? port.port_number,
        controllerId: controller.id,
        controllerName: controller.device_name ?? controller.hostname,
        hostname: controller.hostname,
        portNumber: port.port_number,
        deviceName: port.connected_device_name ?? `Port ${port.port_number}`,
        location: controller.location ?? 'Unassigned',
        tags: (port.tag_ids ?? [])
          .map((tagId) => tagMap.get(tagId))
          .filter((tag): tag is DeviceTag => Boolean(tag)),
        lastSeen: controller.last_seen,
        isOnline: controller.is_online,
        defaultChannel: port.default_channel,
      });
    });
  });

  // Add Virtual Devices (network TVs)
  virtualDevices.forEach((vd) => {
    if (!vd.is_active) {
      return;
    }

    // Find the Virtual Controller for this device
    const virtualController = controllers.find((c) => c.id === vd.controller_id);
    if (!virtualController) {
      console.warn(`[buildRows] Virtual device ${vd.id} references missing controller ${vd.controller_id}`);
      return;
    }

    rows.push({
      id: `vd-${vd.id}`,
      portId: vd.id,
      controllerId: vd.controller_id,
      controllerName: virtualController.device_name ?? virtualController.hostname,
      hostname: virtualController.hostname,
      portNumber: vd.port_number,
      deviceName: vd.device_name,
      location: virtualController.location ?? 'Unassigned',
      tags: [], // Virtual Devices don't have tags yet
      lastSeen: virtualController.last_seen,
      isOnline: vd.is_online,
      defaultChannel: null, // Virtual Devices don't have default channels yet
    });
  });

  console.log(`[buildRows] Built ${rows.length} total rows: ${rows.filter(r => r.id.startsWith('ir-')).length} IR ports, ${rows.filter(r => r.id.startsWith('vd-')).length} virtual devices`);

  return rows;
}

function _formatChannelLabel(channel: ChannelOption): string {
  const parts = [channel.channel_name];
  if (channel.lcn) parts.push(`LCN ${channel.lcn}`);
  if (channel.foxtel_number) parts.push(`Foxtel ${channel.foxtel_number}`);
  return parts.join(' · ');
}

const QueueStatusBar = ({ metrics }: { metrics: { pending: number; processing: number; failed: number; completed_last_hour: number; avg_execution_time_ms: number | null } }) => {
  const totalActive = metrics.pending + metrics.processing;
  const hasActivity = totalActive > 0 || metrics.failed > 0;

  if (!hasActivity) return null;

  return (
    <div className="rounded-xl border border-blue-200 bg-gradient-to-r from-blue-50 to-indigo-50 px-6 py-3 shadow-sm">
      <div className="flex flex-wrap items-center justify-between gap-4">
        <div className="flex items-center gap-6">
          <div className="flex items-center gap-2">
            <div className="h-2 w-2 animate-pulse rounded-full bg-blue-500"></div>
            <span className="text-sm font-semibold text-slate-700">Queue Status</span>
          </div>

          {metrics.processing > 0 && (
            <div className="flex items-center gap-2">
              <div className="h-6 w-6 animate-spin rounded-full border-2 border-blue-200 border-t-blue-600"></div>
              <span className="text-sm text-slate-600">
                <span className="font-semibold text-blue-700">{metrics.processing}</span> processing
              </span>
            </div>
          )}

          {metrics.pending > 0 && (
            <div className="flex items-center gap-2">
              <svg className="h-5 w-5 text-slate-500" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 8v4l3 3m6-3a9 9 0 11-18 0 9 9 0 0118 0z" />
              </svg>
              <span className="text-sm text-slate-600">
                <span className="font-semibold text-slate-700">{metrics.pending}</span> pending
              </span>
            </div>
          )}

          {metrics.failed > 0 && (
            <div className="flex items-center gap-2">
              <svg className="h-5 w-5 text-red-500" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 8v4m0 4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
              </svg>
              <span className="text-sm text-slate-600">
                <span className="font-semibold text-red-600">{metrics.failed}</span> failed
              </span>
            </div>
          )}
        </div>

        <div className="flex items-center gap-4 text-xs text-slate-500">
          {metrics.completed_last_hour > 0 && (
            <span>{metrics.completed_last_hour} completed (last hour)</span>
          )}
          {metrics.avg_execution_time_ms && (
            <span>Avg: {metrics.avg_execution_time_ms}ms</span>
          )}
        </div>
      </div>
    </div>
  );
};
