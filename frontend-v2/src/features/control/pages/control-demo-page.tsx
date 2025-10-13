import { useEffect, useMemo, useState } from 'react';
import { useManagedDevices } from '@/features/devices/hooks/use-managed-devices';
import { useDeviceTags } from '@/features/settings/hooks/use-device-tags';
import { useAvailableChannels } from '@/features/devices/hooks/use-available-channels';
import { useQueueMetrics } from '@/features/devices/hooks/use-queue-metrics';
import { sendBulkCommand } from '@/features/devices/api/devices-api';
import type { ChannelOption, DeviceTag, ManagedDevice } from '@/types';
import { GlassmorphicDeviceCard } from '../components/glassmorphic-device-card';
import { ThemeSelector } from '../components/theme-selector';
import { GlassmorphicActionToolbar } from '../components/glassmorphic-action-toolbar';
import { useVirtualDevices } from '@/features/devices/hooks/use-virtual-devices';
import { ChannelSelectorModal } from '../components/channel-selector-modal';

type Theme = {
  id: string;
  name: string;
  description: string;
  colors: {
    gradientFrom: string;
    gradientVia?: string;
    gradientTo: string;
    cardBg: string;
    cardBorder: string;
    cardBorderHover: string;
    primary: string;
    primaryHover: string;
    secondary: string;
    accent: string;
    textPrimary: string;
    textSecondary: string;
    success: string;
    danger: string;
    warning: string;
  };
};

const themes: Theme[] = [
  {
    id: 'neon-club',
    name: 'Neon Club',
    description: 'Vibrant pink and purple for high-energy venues',
    colors: {
      gradientFrom: '#667eea',
      gradientVia: '#764ba2',
      gradientTo: '#f093fb',
      cardBg: 'rgba(255, 255, 255, 0.1)',
      cardBorder: 'rgba(255, 255, 255, 0.2)',
      cardBorderHover: '#FF006E',
      primary: '#FF006E',
      primaryHover: '#D4005E',
      secondary: '#8338EC',
      accent: '#00F5FF',
      textPrimary: '#ffffff',
      textSecondary: 'rgba(255, 255, 255, 0.7)',
      success: '#10B981',
      danger: '#EF4444',
      warning: '#F59E0B',
    },
  },
  {
    id: 'sports-bar',
    name: 'Sports Bar',
    description: 'Electric blue and orange for sports venues',
    colors: {
      gradientFrom: '#1e3a8a',
      gradientVia: '#3b82f6',
      gradientTo: '#60a5fa',
      cardBg: 'rgba(255, 255, 255, 0.1)',
      cardBorder: 'rgba(255, 255, 255, 0.2)',
      cardBorderHover: '#00D9FF',
      primary: '#00D9FF',
      primaryHover: '#00B8D4',
      secondary: '#F97316',
      accent: '#10B981',
      textPrimary: '#ffffff',
      textSecondary: 'rgba(255, 255, 255, 0.7)',
      success: '#10B981',
      danger: '#EF4444',
      warning: '#F59E0B',
    },
  },
  {
    id: 'premium-lounge',
    name: 'Premium Lounge',
    description: 'Sophisticated gold and deep slate',
    colors: {
      gradientFrom: '#0f172a',
      gradientVia: '#1e293b',
      gradientTo: '#334155',
      cardBg: 'rgba(255, 255, 255, 0.08)',
      cardBorder: 'rgba(255, 255, 255, 0.15)',
      cardBorderHover: '#FFD700',
      primary: '#FFD700',
      primaryHover: '#FFC700',
      secondary: '#06b6d4',
      accent: '#8b5cf6',
      textPrimary: '#ffffff',
      textSecondary: 'rgba(255, 255, 255, 0.6)',
      success: '#10B981',
      danger: '#EF4444',
      warning: '#F59E0B',
    },
  },
  {
    id: 'sunset-lounge',
    name: 'Sunset Lounge',
    description: 'Warm sunset colors for relaxed atmosphere',
    colors: {
      gradientFrom: '#ec4899',
      gradientVia: '#f97316',
      gradientTo: '#fbbf24',
      cardBg: 'rgba(255, 255, 255, 0.12)',
      cardBorder: 'rgba(255, 255, 255, 0.2)',
      cardBorderHover: '#fbbf24',
      primary: '#fbbf24',
      primaryHover: '#f59e0b',
      secondary: '#ec4899',
      accent: '#f97316',
      textPrimary: '#ffffff',
      textSecondary: 'rgba(255, 255, 255, 0.8)',
      success: '#10B981',
      danger: '#EF4444',
      warning: '#F59E0B',
    },
  },
  {
    id: 'ocean-breeze',
    name: 'Ocean Breeze',
    description: 'Cool teal and cyan for coastal venues',
    colors: {
      gradientFrom: '#0e7490',
      gradientVia: '#06b6d4',
      gradientTo: '#22d3ee',
      cardBg: 'rgba(255, 255, 255, 0.1)',
      cardBorder: 'rgba(255, 255, 255, 0.2)',
      cardBorderHover: '#22d3ee',
      primary: '#22d3ee',
      primaryHover: '#06b6d4',
      secondary: '#3b82f6',
      accent: '#8b5cf6',
      textPrimary: '#ffffff',
      textSecondary: 'rgba(255, 255, 255, 0.7)',
      success: '#10B981',
      danger: '#EF4444',
      warning: '#F59E0B',
    },
  },
];

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

  const hybridIRPorts = new Set<string>();
  virtualDevices.forEach((vd) => {
    if (vd.fallback_ir_controller && vd.fallback_ir_port) {
      hybridIRPorts.add(`${vd.fallback_ir_controller}:${vd.fallback_ir_port}`);
    }
  });

  controllers.forEach((controller) => {
    if (controller.device_type === 'virtual_controller') {
      return;
    }

    controller.ir_ports.forEach((port) => {
      if (!port.is_active || port.port_number === 0) {
        return;
      }

      const portKey = `${controller.hostname}:${port.port_number}`;
      if (hybridIRPorts.has(portKey)) {
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

  virtualDevices.forEach((vd) => {
    if (!vd.is_active) {
      return;
    }

    const virtualController = controllers.find((c) => c.id === vd.controller_id);
    if (!virtualController) {
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
      tags: [],
      lastSeen: virtualController.last_seen,
      isOnline: vd.is_online,
      defaultChannel: null,
    });
  });

  return rows;
}

export const ControlDemoPage = () => {
  const { data: controllers = [], isLoading } = useManagedDevices();
  const { data: tags = [] } = useDeviceTags();
  const { data: channels = [] } = useAvailableChannels();
  const { data: queueMetrics } = useQueueMetrics();
  const { data: virtualDevices = [] } = useVirtualDevices();

  const [currentTheme, setCurrentTheme] = useState<Theme>(themes[0]);
  const [selectedIds, setSelectedIds] = useState<Set<string>>(new Set());
  const [nameFilter, setNameFilter] = useState('');
  const [collapsedLocations, setCollapsedLocations] = useState<Set<string>>(new Set());
  const [showChannelModal, setShowChannelModal] = useState(false);

  const rows = useMemo(() => buildRows(controllers, tags, virtualDevices), [controllers, tags, virtualDevices]);

  const displayRows = useMemo(() => {
    const lowered = nameFilter.trim().toLowerCase();
    return rows.filter((row) => {
      if (lowered && !row.deviceName.toLowerCase().includes(lowered)) {
        return false;
      }
      return true;
    });
  }, [rows, nameFilter]);

  useEffect(() => {
    const validIds = new Set(displayRows.map((row) => row.id));
    setSelectedIds((prev) => {
      const filtered = [...prev].filter((id) => validIds.has(id));
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

  const selectedRows = useMemo(() => rows.filter((row) => selectedIds.has(row.id)), [rows, selectedIds]);

  const toggleAll = () => {
    const currentIds = displayRows.map((row) => row.id);
    const allSelected = currentIds.every((id) => selectedIds.has(id));
    setSelectedIds(allSelected ? new Set() : new Set(currentIds));
  };

  return (
    <div
      className="min-h-screen transition-all duration-700"
      style={{
        background: `linear-gradient(135deg, ${currentTheme.colors.gradientFrom}, ${currentTheme.colors.gradientVia || currentTheme.colors.gradientTo}, ${currentTheme.colors.gradientTo})`,
      }}
    >
      {/* Theme Selector */}
      <ThemeSelector currentTheme={currentTheme} onThemeChange={setCurrentTheme} />

      {/* Action Toolbar */}
      <GlassmorphicActionToolbar
        selectedRows={selectedRows}
        totalRows={displayRows.length}
        onOpenChannelModal={() => setShowChannelModal(true)}
        toggleAll={toggleAll}
        theme={currentTheme}
      />

      {/* Main Content */}
      <div className="mx-auto max-w-[1600px] px-6 py-6 pr-80">
        {/* Header */}
        <div className="mb-8 text-center">
          <h1
            className="mb-2 text-5xl font-black tracking-tight"
            style={{ color: currentTheme.colors.textPrimary }}
          >
            TapCommand Control
          </h1>
          <p
            className="text-xl font-medium"
            style={{ color: currentTheme.colors.textSecondary }}
          >
            {currentTheme.description}
          </p>
        </div>

        {/* Queue Status */}
        {queueMetrics && (queueMetrics.pending > 0 || queueMetrics.processing > 0 || queueMetrics.failed > 0) && (
          <div
            className="mb-6 rounded-3xl p-6 backdrop-blur-xl"
            style={{
              backgroundColor: currentTheme.colors.cardBg,
              border: `2px solid ${currentTheme.colors.cardBorder}`,
            }}
          >
            <div className="flex items-center gap-6">
              <div className="flex items-center gap-2">
                <div
                  className="h-3 w-3 animate-pulse rounded-full"
                  style={{ backgroundColor: currentTheme.colors.accent }}
                />
                <span
                  className="text-lg font-bold"
                  style={{ color: currentTheme.colors.textPrimary }}
                >
                  Queue Status
                </span>
              </div>
              {queueMetrics.processing > 0 && (
                <span style={{ color: currentTheme.colors.textSecondary }}>
                  <span style={{ color: currentTheme.colors.accent }} className="font-bold">
                    {queueMetrics.processing}
                  </span>{' '}
                  processing
                </span>
              )}
              {queueMetrics.pending > 0 && (
                <span style={{ color: currentTheme.colors.textSecondary }}>
                  <span style={{ color: currentTheme.colors.textPrimary }} className="font-bold">
                    {queueMetrics.pending}
                  </span>{' '}
                  pending
                </span>
              )}
            </div>
          </div>
        )}

        {/* Device Groups */}
        {isLoading ? (
          <div
            className="rounded-3xl p-12 text-center backdrop-blur-xl"
            style={{
              backgroundColor: currentTheme.colors.cardBg,
              border: `2px solid ${currentTheme.colors.cardBorder}`,
              color: currentTheme.colors.textPrimary,
            }}
          >
            <div className="text-2xl font-bold">Loading devices...</div>
          </div>
        ) : (
          <div className="space-y-6">
            {Array.from(rowsByLocation.entries())
              .sort(([a], [b]) => a.localeCompare(b))
              .map(([location, locationRows]) => {
                const isCollapsed = collapsedLocations.has(location);
                const onlineCount = locationRows.filter((r) => r.isOnline).length;
                const selectedInLocation = locationRows.filter((r) => selectedIds.has(r.id)).length;

                return (
                  <div
                    key={location}
                    className="overflow-hidden rounded-3xl backdrop-blur-xl transition-all"
                    style={{
                      backgroundColor: currentTheme.colors.cardBg,
                      border: `2px solid ${currentTheme.colors.cardBorder}`,
                    }}
                  >
                    {/* Location Header */}
                    <div className="flex items-center justify-between p-6">
                      <button
                        type="button"
                        onClick={() => toggleLocation(location)}
                        className="flex flex-1 items-center gap-4 text-left transition-all hover:scale-[1.01]"
                      >
                        <svg
                          className={`h-8 w-8 transition-transform ${isCollapsed ? '' : 'rotate-90'}`}
                          fill="none"
                          stroke="currentColor"
                          viewBox="0 0 24 24"
                          style={{ color: currentTheme.colors.textSecondary }}
                        >
                          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={3} d="M9 5l7 7-7 7" />
                        </svg>
                        <h2
                          className="text-3xl font-black"
                          style={{ color: currentTheme.colors.textPrimary }}
                        >
                          {location}
                        </h2>
                        <span
                          className="text-lg font-medium"
                          style={{ color: currentTheme.colors.textSecondary }}
                        >
                          {locationRows.length} device{locationRows.length === 1 ? '' : 's'} • {onlineCount} online
                        </span>
                        {selectedInLocation > 0 && (
                          <span
                            className="rounded-full px-4 py-2 text-sm font-bold"
                            style={{
                              backgroundColor: `${currentTheme.colors.primary}40`,
                              color: currentTheme.colors.textPrimary,
                              border: `2px solid ${currentTheme.colors.primary}`,
                            }}
                          >
                            {selectedInLocation} selected
                          </span>
                        )}
                      </button>

                      {/* Location Actions */}
                      <div className="flex items-center gap-3">
                        <button
                          type="button"
                          onClick={async (e) => {
                            e.stopPropagation();
                            const rowsToControl = selectedInLocation > 0
                              ? locationRows.filter((r) => selectedIds.has(r.id))
                              : locationRows;
                            const targets = rowsToControl.map((row) => ({
                              hostname: row.hostname,
                              port: row.portNumber,
                            }));
                            await sendBulkCommand({ targets, command: 'power_on', priority: 5 });
                          }}
                          className="min-h-[56px] rounded-2xl px-6 font-bold transition-all hover:scale-105 active:scale-95"
                          style={{
                            backgroundColor: `${currentTheme.colors.success}40`,
                            border: `2px solid ${currentTheme.colors.success}`,
                            color: currentTheme.colors.textPrimary,
                            boxShadow: `0 4px 15px ${currentTheme.colors.success}30`,
                          }}
                        >
                          ⚡ ON
                        </button>
                        <button
                          type="button"
                          onClick={async (e) => {
                            e.stopPropagation();
                            const rowsToControl = selectedInLocation > 0
                              ? locationRows.filter((r) => selectedIds.has(r.id))
                              : locationRows;
                            const targets = rowsToControl.map((row) => ({
                              hostname: row.hostname,
                              port: row.portNumber,
                            }));
                            await sendBulkCommand({ targets, command: 'power_off', priority: 5 });
                          }}
                          className="min-h-[56px] rounded-2xl px-6 font-bold transition-all hover:scale-105 active:scale-95"
                          style={{
                            backgroundColor: `${currentTheme.colors.danger}40`,
                            border: `2px solid ${currentTheme.colors.danger}`,
                            color: currentTheme.colors.textPrimary,
                            boxShadow: `0 4px 15px ${currentTheme.colors.danger}30`,
                          }}
                        >
                          ⚡ OFF
                        </button>
                        <button
                          type="button"
                          onClick={(e) => {
                            e.stopPropagation();
                            selectAllInLocation(location);
                          }}
                          className="min-h-[56px] rounded-2xl px-6 font-bold transition-all hover:scale-105 active:scale-95"
                          style={{
                            backgroundColor: `${currentTheme.colors.primary}30`,
                            border: `2px solid ${currentTheme.colors.primary}`,
                            color: currentTheme.colors.textPrimary,
                            boxShadow: `0 4px 15px ${currentTheme.colors.primary}30`,
                          }}
                        >
                          {selectedInLocation === locationRows.length ? 'Deselect All' : 'Select All'}
                        </button>
                      </div>
                    </div>

                    {/* Device Grid */}
                    {!isCollapsed && (
                      <div className="border-t p-6" style={{ borderColor: currentTheme.colors.cardBorder }}>
                        <div className="grid gap-6 md:grid-cols-2 xl:grid-cols-3 2xl:grid-cols-4">
                          {locationRows.map((row) => (
                            <GlassmorphicDeviceCard
                              key={row.id}
                              row={row}
                              channels={channels}
                              selected={selectedIds.has(row.id)}
                              onToggle={() => toggleSelection(row.id)}
                              onTagSelect={quickSelectTag}
                              theme={currentTheme}
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

        {/* Floating Action Button */}
        {selectedIds.size > 0 && (
          <button
            type="button"
            onClick={() => setShowChannelModal(true)}
            className="fixed bottom-8 right-8 z-30 rounded-full p-6 text-white shadow-2xl transition-all hover:scale-110 active:scale-95"
            style={{
              backgroundColor: currentTheme.colors.primary,
              boxShadow: `0 0 40px ${currentTheme.colors.primary}80, 0 20px 40px rgba(0,0,0,0.4)`,
            }}
          >
            <svg className="h-10 w-10" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path
                strokeLinecap="round"
                strokeLinejoin="round"
                strokeWidth={2}
                d="M7 4v16M17 4v16M3 8h4m10 0h4M3 12h18M3 16h4m10 0h4M4 20h16a1 1 0 001-1V5a1 1 0 00-1-1H4a1 1 0 00-1 1v14a1 1 0 001 1z"
              />
            </svg>
          </button>
        )}
      </div>

      {/* Channel Modal */}
      <ChannelSelectorModal
        isOpen={showChannelModal}
        onClose={() => setShowChannelModal(false)}
        channels={channels}
        controllers={controllers}
        selectedDeviceCount={selectedIds.size}
        onSelectChannel={async (channelLcn) => {
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
    </div>
  );
};
