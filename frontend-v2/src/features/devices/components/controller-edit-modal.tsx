import { useEffect, useMemo, useState } from 'react';
import type { ChannelOption, ManagedDevice, DiscoveredDevice, IRPort } from '@/types';
import { useUpdateManagedDevice } from '../hooks/use-update-managed-device';
import { useDeleteManagedDevice } from '../hooks/use-delete-managed-device';
import { useConnectDiscoveredDevice } from '../../discovery/hooks/use-connect-device';
import type { ManagedDeviceUpdatePayload } from '../api/devices-api';
import { useApplicationSettings } from '@/features/settings/hooks/use-application-settings';
import { useDeviceTags } from '@/features/settings/hooks/use-device-tags';
import { useAvailableChannels } from '../hooks/use-available-channels';
import { useManagedDevices } from '../hooks/use-managed-devices';
import { useLibraryCommands } from '../hooks/use-library-commands';

interface ManagedModalProps {
  device: ManagedDevice;
  open: boolean;
  onClose: () => void;
  onSaved?: () => void;
}

interface DiscoveredModalProps {
  discovered: DiscoveredDevice;
  open: boolean;
  onClose: () => void;
  onSaved?: () => void;
}

type ControllerEditModalProps = (
  | ({ device: ManagedDevice } & ManagedModalProps)
  | ({ discovered: DiscoveredDevice } & DiscoveredModalProps)
) & { device?: ManagedDevice; discovered?: DiscoveredDevice };

export const ControllerEditModal = (props: ControllerEditModalProps) => {
  if (!props.open) {
    return null;
  }

  if ('device' in props && props.device) {
    return <ManagedControllerModal {...props} device={props.device} />;
  }

  if ('discovered' in props && props.discovered) {
    return <DiscoveryControllerModal {...props} discovered={props.discovered} />;
  }

  return null;
};

const ManagedControllerModal = ({ device, open, onClose, onSaved }: ManagedModalProps) => {
  const mutation = useUpdateManagedDevice();
  const deleteMutation = useDeleteManagedDevice();
  const { data: settings } = useApplicationSettings(true);
  const { data: tags, isLoading: tagsLoading } = useDeviceTags();
  const { data: channels, isLoading: channelsLoading } = useAvailableChannels();
  const { data: allDevices } = useManagedDevices();
  const globalApiKey =
    settings && typeof settings['esphome_api_key']?.value === 'string'
      ? (settings['esphome_api_key'].value as string)
      : '';

  const [deviceName, setDeviceName] = useState(device.device_name ?? '');
  const [location, setLocation] = useState(device.location ?? '');
  const [notes, setNotes] = useState(device.notes ?? '');
  const [errorMessage, setErrorMessage] = useState<string | null>(null);
  const [ports, setPorts] = useState<PortFormState[]>(() => mapPorts(device.ir_ports));
  const [apiKeyInput, setApiKeyInput] = useState(device.api_key ?? '');
  const [showLocationDropdown, setShowLocationDropdown] = useState(false);

  useEffect(() => {
    if (!open) return;
    setDeviceName(device.device_name ?? '');
    setLocation(device.location ?? '');
    setNotes(device.notes ?? '');
    setPorts(mapPorts(device.ir_ports));
    setApiKeyInput(device.api_key ?? '');
    setErrorMessage(null);
  }, [device, open]);

  const portCapabilities = useMemo(() => extractPortCapabilities(device.capabilities), [device.capabilities]);
  const brandSummary = useMemo(() => extractBrands(device.capabilities), [device.capabilities]);
  const tagOptions = tags ?? [];
  // Calculate channel usage for categorization
  const channelUsage = useMemo(() => {
    const usage = new Map<string, number>();
    (allDevices ?? []).forEach((controller) => {
      controller.ir_ports.forEach((port) => {
        if (port.default_channel) {
          usage.set(port.default_channel, (usage.get(port.default_channel) || 0) + 1);
        }
      });
    });
    return usage;
  }, [allDevices]);

  // Categorized channel options for grouped dropdown
  const categorizedChannelOptions = useMemo(() => {
    const categories = {
      'In Use': [] as Array<{ value: string; label: string; channel: ChannelOption }>,
      'InHouse': [] as Array<{ value: string; label: string; channel: ChannelOption }>,
      'Sports': [] as Array<{ value: string; label: string; channel: ChannelOption }>,
      'News': [] as Array<{ value: string; label: string; channel: ChannelOption }>,
      'FTA': [] as Array<{ value: string; label: string; channel: ChannelOption }>,
      'Entertainment': [] as Array<{ value: string; label: string; channel: ChannelOption }>,
      'Kids': [] as Array<{ value: string; label: string; channel: ChannelOption }>,
      'Other': [] as Array<{ value: string; label: string; channel: ChannelOption }>,
    };

    (channels ?? []).forEach((channel) => {
      const option = {
        value: channel.foxtel_number || `${channel.id}`,
        label: formatChannelLabel(channel),
        channel,
      };

      // In Use
      const lcn = channel.lcn?.split('/')[0].trim() || '';
      if (channelUsage.has(lcn) || channelUsage.has(channel.foxtel_number || '')) {
        categories['In Use'].push(option);
      }

      // InHouse
      if (channel.platform === 'InHouse') {
        categories['InHouse'].push(option);
      }

      // FTA
      if (channel.platform === 'FTA') {
        categories['FTA'].push(option);
      }

      // Foxtel categorization by number range
      if (channel.foxtel_number) {
        const foxtelNum = parseInt(channel.foxtel_number, 10);
        if (foxtelNum >= 500 && foxtelNum < 600) {
          categories['Sports'].push(option);
        } else if (foxtelNum >= 600 && foxtelNum < 700) {
          if (
            channel.channel_name.toLowerCase().includes('news') ||
            channel.channel_name.toLowerCase().includes('cnn') ||
            channel.channel_name.toLowerCase().includes('bbc')
          ) {
            categories['News'].push(option);
          } else {
            categories['Entertainment'].push(option);
          }
        } else if (foxtelNum >= 700 && foxtelNum < 800) {
          categories['Kids'].push(option);
        } else {
          categories['Entertainment'].push(option);
        }
      } else if (!channel.platform) {
        categories['Other'].push(option);
      }
    });

    // Sort In Use by usage count
    categories['In Use'].sort((a, b) => {
      const aLcn = a.channel.lcn?.split('/')[0].trim() || a.channel.foxtel_number || '';
      const bLcn = b.channel.lcn?.split('/')[0].trim() || b.channel.foxtel_number || '';
      return (channelUsage.get(bLcn) || 0) - (channelUsage.get(aLcn) || 0);
    });

    return categories;
  }, [channels, channelUsage]);

  const channelSelectOptions = useMemo(
    () =>
      (channels ?? []).map((channel) => ({
        value: channel.foxtel_number || `${channel.id}`,
        label: formatChannelLabel(channel),
      })),
    [channels],
  );
  const visiblePorts = useMemo(
    () => ports.filter((port) => portCapabilities.has(port.port_number)),
    [ports, portCapabilities]
  );
  const modalHeightClass =
    visiblePorts.length === 1 ? 'h-auto max-h-[85vh]' :
    visiblePorts.length === 2 ? 'h-auto max-h-[90vh]' :
    'h-[90vh]';
  const existingLocations = useMemo(() => {
    if (!allDevices) return [];
    const locations = allDevices
      .map(d => d.location)
      .filter((loc): loc is string => Boolean(loc?.trim()));
    return Array.from(new Set(locations)).sort();
  }, [allDevices]);

  const handlePortToggle = (portNumber: number, value: boolean) => {
    setPorts((prev) =>
      prev.map((port) => (port.port_number === portNumber ? { ...port, is_active: value } : port)),
    );
  };

  const handlePortNameChange = (portNumber: number, value: string) => {
    setPorts((prev) =>
      prev.map((port) => (port.port_number === portNumber ? { ...port, connected_device_name: value } : port)),
    );
  };

  const handlePortTagToggle = (portNumber: number, tagId: number, checked: boolean) => {
    setPorts((prev) =>
      prev.map((port) => {
        if (port.port_number !== portNumber) return port;
        const current = new Set(port.tag_ids);
        if (checked) {
          current.add(tagId);
        } else {
          current.delete(tagId);
        }
        return { ...port, tag_ids: Array.from(current).sort((a, b) => a - b) };
      }),
    );
  };

  const handlePortDefaultChannelSelect = (portNumber: number, value: string) => {
    setPorts((prev) =>
      prev.map((port) => {
        if (port.port_number !== portNumber) return port;
        if (value === '') {
          return { ...port, default_channel_source: 'none', default_channel: null };
        }
        if (value === '__custom__') {
          const existing = port.default_channel_source === 'custom' ? port.default_channel ?? '' : '';
          return { ...port, default_channel_source: 'custom', default_channel: existing };
        }
        return { ...port, default_channel_source: 'option', default_channel: value };
      }),
    );
  };

  const handleCustomDefaultChannelChange = (portNumber: number, value: string) => {
    setPorts((prev) =>
      prev.map((port) =>
        port.port_number === portNumber
          ? { ...port, default_channel_source: 'custom', default_channel: value }
          : port,
      ),
    );
  };

  const handleSubmit = async (event: React.FormEvent) => {
    event.preventDefault();
    setErrorMessage(null);

    const payload: ManagedDeviceUpdatePayload = {
      device_name: sanitizeValue(deviceName),
      api_key: apiKeyInput.trim() ? apiKeyInput.trim() : null,
      venue_name: null,
      location: sanitizeValue(location),
      notes: notes.length ? notes : null,
      ir_ports: ports.map((port) => ({
        port_number: port.port_number,
        connected_device_name: sanitizeValue(port.connected_device_name),
        is_active: port.is_active,
        cable_length: port.cable_length,
        installation_notes: port.installation_notes,
        tag_ids: port.tag_ids.length ? port.tag_ids : [],
        default_channel:
          port.default_channel_source === 'custom'
            ? sanitizeValue(port.default_channel ?? '')
            : port.default_channel_source === 'option'
            ? port.default_channel
            : null,
        device_number: port.device_number,
      })),
    };

    try {
      await mutation.mutateAsync({ deviceId: device.id, payload });
      if (onSaved) {
        onSaved();
      } else {
        onClose();
      }
    } catch (error) {
      const message = error instanceof Error ? error.message : 'Failed to update controller.';
      setErrorMessage(message);
    }
  };

  const handleDelete = async () => {
    if (deleteMutation.isPending) return;
    const confirmed = window.confirm(
      `Remove ${device.device_name ?? device.hostname} from management? This will delete its port assignments.`,
    );
    if (!confirmed) return;

    try {
      await deleteMutation.mutateAsync(device.id);
      if (onSaved) {
        onSaved();
      } else {
        onClose();
      }
    } catch (error) {
      const message = error instanceof Error ? error.message : 'Failed to delete controller.';
      setErrorMessage(message);
    }
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center">
      <div className="absolute inset-0 bg-slate-900/40" aria-hidden="true" onClick={onClose} />
      <div
        role="dialog"
        aria-modal="true"
        className={`relative z-10 ${modalHeightClass} w-full max-w-3xl overflow-hidden rounded-xl bg-white shadow-xl`}
      >
        <form className="flex h-full flex-col" onSubmit={handleSubmit}>
          <header className="border-b border-slate-200 px-6 py-4">
            <div className="flex items-center justify-between">
              <h3 className="text-lg font-semibold text-slate-900">Edit Controller</h3>
              <p className="text-sm text-slate-500">{device.hostname}</p>
            </div>
            {brandSummary.length ? (
              <p className="mt-2 text-xs text-slate-500">Capabilities: {brandSummary.join(', ')}</p>
            ) : null}
          </header>

          <div className="flex-1 overflow-y-auto px-6 py-4">
            <section className="space-y-4">
              <div className="grid gap-4 md:grid-cols-2">
                <div className="flex items-center gap-3">
                  <label className="text-sm font-medium text-slate-700 whitespace-nowrap">
                    Controller name
                  </label>
                  <input
                    type="text"
                    value={deviceName}
                    onChange={(event) => setDeviceName(event.target.value)}
                    className="flex-1 rounded-md border border-slate-300 px-3 py-2 text-sm text-slate-900 shadow-sm focus:border-brand-500 focus:outline-none focus:ring-1 focus:ring-brand-500"
                  />
                </div>
                <div className="flex flex-col gap-1">
                  <div className="flex items-center gap-3">
                    <label className="text-sm font-medium text-slate-700 whitespace-nowrap">
                      Location
                    </label>
                    <div className="relative flex-1">
                      <input
                        type="text"
                        value={location}
                        onChange={(event) => setLocation(event.target.value)}
                        onFocus={() => setShowLocationDropdown(true)}
                        onBlur={() => setTimeout(() => setShowLocationDropdown(false), 200)}
                        placeholder="Select existing or enter new location"
                        className="w-full rounded-md border border-slate-300 px-3 py-2 pr-8 text-sm text-slate-900 shadow-sm focus:border-brand-500 focus:outline-none focus:ring-1 focus:ring-brand-500"
                      />
                      {existingLocations.length > 0 && (
                        <div className="pointer-events-none absolute inset-y-0 right-0 flex items-center pr-2">
                          <svg className="h-4 w-4 text-slate-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 9l-7 7-7-7" />
                          </svg>
                        </div>
                      )}

                      {/* Dropdown with existing locations */}
                      {showLocationDropdown && existingLocations.length > 0 && (
                        <div className="absolute z-10 mt-1 max-h-60 w-full overflow-auto rounded-md border border-slate-200 bg-white py-1 shadow-lg">
                          {existingLocations
                            .filter((loc) => {
                              // Show all locations if input is empty or show filtered results
                              if (!location.trim()) return true;
                              return loc.toLowerCase().includes(location.toLowerCase());
                            })
                            .map((loc) => (
                              <button
                                key={loc}
                                type="button"
                                onClick={() => {
                                  setLocation(loc);
                                  setShowLocationDropdown(false);
                                }}
                                className="w-full px-3 py-2 text-left text-sm text-slate-900 hover:bg-brand-50 hover:text-brand-700"
                              >
                                {loc}
                              </button>
                            ))}
                          {location.trim() && !existingLocations.some((loc) => loc.toLowerCase() === location.toLowerCase()) && (
                            <div className="border-t border-slate-200 px-3 py-2 text-xs text-slate-500">
                              Press Enter to create "{location}"
                            </div>
                          )}
                        </div>
                      )}
                    </div>
                  </div>
                  {existingLocations.length > 0 && (
                    <p className="text-xs text-slate-500 pl-24">
                      {existingLocations.length} existing location{existingLocations.length === 1 ? '' : 's'}
                    </p>
                  )}
                </div>
              </div>

              <div className="grid gap-4 md:grid-cols-2">
                <div className="flex items-center gap-3">
                  <label className="text-sm font-medium text-slate-700 whitespace-nowrap">
                    Notes
                  </label>
                  <input
                    type="text"
                    value={notes}
                    onChange={(event) => setNotes(event.target.value)}
                    className="flex-1 rounded-md border border-slate-300 px-3 py-2 text-sm text-slate-900 shadow-sm focus:border-brand-500 focus:outline-none focus:ring-1 focus:ring-brand-500"
                  />
                </div>
                <div className="flex items-center gap-3">
                  <label className="text-sm font-medium text-slate-700 whitespace-nowrap">
                    API key
                  </label>
                  <input
                    type="text"
                    value={apiKeyInput}
                    onChange={(event) => setApiKeyInput(event.target.value)}
                    placeholder={globalApiKey ? `${globalApiKey} (application key)` : 'Uses application key'}
                    className="flex-1 rounded-md border border-slate-300 px-3 py-2 text-sm text-slate-900 shadow-sm focus:border-brand-500 focus:outline-none focus:ring-1 focus:ring-brand-500"
                  />
                </div>
              </div>

              <p className="text-xs text-slate-500">
                Leave API key blank to use the application API key. Enter a custom key to override it for this controller.
              </p>

              <div className="space-y-3">
                <h4 className="text-sm font-semibold text-slate-900">Ports</h4>
                <div className="space-y-3">
                  {visiblePorts.map((port) => {
                    const capability = portCapabilities.get(port.port_number);
                    const selectValue = resolveChannelSelectValue(port, channelSelectOptions);
                    const isCustomChannel = selectValue === '__custom__';
                    const customChannelValue = isCustomChannel ? port.default_channel ?? '' : '';
                    const needsFallbackOption =
                      selectValue !== '' &&
                      selectValue !== '__custom__' &&
                      !channelSelectOptions.some((option) => option.value === selectValue);
                    return (
                      <div
                        key={port.port_number}
                        className="rounded-lg border border-slate-200 bg-slate-50/60 px-4 py-3"
                      >
                        <div className="flex flex-wrap items-center justify-between gap-2">
                          <div>
                            <p className="text-sm font-semibold text-slate-900">Port {port.port_number}</p>
                            {capability?.description ? (
                              <p className="text-xs text-slate-500">{capability.description}</p>
                            ) : capability?.brand ? (
                              <p className="text-xs text-slate-500">{capability.brand}</p>
                            ) : null}
                          </div>
                          <div className="flex items-center gap-2">
                            <PortAvailableCommandsInline libraryId={capability?.lib} />
                            <label className="flex items-center gap-2 text-xs font-medium text-slate-600 whitespace-nowrap">
                              <input
                                type="checkbox"
                                checked={port.is_active}
                                onChange={(event) => handlePortToggle(port.port_number, event.target.checked)}
                                className="h-4 w-4 rounded border-slate-300 text-brand-600 focus:ring-brand-500"
                              />
                              Active
                            </label>
                          </div>
                        </div>

                        <div className="mt-2 grid gap-2 md:grid-cols-2">
                          <div className="flex items-center gap-2">
                            <label className="text-xs font-medium text-slate-600 whitespace-nowrap">
                              Connected device
                            </label>
                            <input
                              type="text"
                              value={port.connected_device_name}
                              onChange={(event) => handlePortNameChange(port.port_number, event.target.value)}
                              placeholder={`Port ${port.port_number}`}
                              className="flex-1 rounded-md border border-slate-300 px-3 py-1.5 text-sm text-slate-900 shadow-sm focus:border-brand-500 focus:outline-none focus:ring-1 focus:ring-brand-500"
                            />
                          </div>
                          <div className="flex flex-col gap-2">
                            <div className="flex items-center gap-2">
                              <label className="text-xs font-medium text-slate-600 whitespace-nowrap">
                                Default channel
                              </label>
                              <select
                                value={selectValue}
                                onChange={(event) =>
                                  handlePortDefaultChannelSelect(port.port_number, event.target.value)
                                }
                                disabled={channelsLoading}
                                className="w-40 rounded-md border border-slate-300 px-3 py-1.5 text-sm text-slate-900 shadow-sm focus:border-brand-500 focus:outline-none focus:ring-1 focus:ring-brand-500"
                              >
                                <option value="">No default channel</option>
                                {needsFallbackOption ? (
                                  <option value={selectValue}>Current selection</option>
                                ) : null}

                                {/* Grouped channel options */}
                                {Object.entries(categorizedChannelOptions).map(([category, options]) => {
                                  if (options.length === 0) return null;
                                  return (
                                    <optgroup key={category} label={category}>
                                      {options.map((option) => (
                                        <option key={option.value} value={option.value}>
                                          {option.label}
                                        </option>
                                      ))}
                                    </optgroup>
                                  );
                                })}

                                <option value="__custom__">Custom value…</option>
                              </select>
                            </div>
                            {isCustomChannel ? (
                              <input
                                type="text"
                                value={customChannelValue}
                                onChange={(event) =>
                                  handleCustomDefaultChannelChange(port.port_number, event.target.value)
                                }
                                placeholder="Enter channel identifier"
                                className="rounded-md border border-slate-300 px-3 py-1.5 text-sm text-slate-900 shadow-sm focus:border-brand-500 focus:outline-none focus:ring-1 focus:ring-brand-500"
                              />
                            ) : null}
                          </div>
                        </div>

                        <div className="mt-2 flex items-start gap-2 text-xs font-medium text-slate-600">
                          <span className="whitespace-nowrap pt-1">Tags</span>
                          {tagsLoading ? (
                            <span className="text-slate-500">Loading tags…</span>
                          ) : tagOptions.length ? (
                            <div className="flex flex-wrap gap-2">
                              {tagOptions.map((tag) => {
                                const checked = port.tag_ids.includes(tag.id);
                                return (
                                  <label
                                    key={tag.id}
                                    className={`inline-flex items-center gap-1 rounded-full border px-2 py-1 text-xs font-medium shadow-sm transition ${
                                      checked
                                        ? 'border-brand-200 bg-brand-50 text-brand-700'
                                        : 'border-slate-200 bg-white text-slate-600 hover:border-brand-200'
                                    }`}
                                    style={tag.color ? { borderColor: checked ? tag.color : undefined } : undefined}
                                  >
                                    <input
                                      type="checkbox"
                                      checked={checked}
                                      onChange={(event) =>
                                        handlePortTagToggle(port.port_number, tag.id, event.target.checked)
                                      }
                                      className="h-3.5 w-3.5 rounded border-slate-300 text-brand-600 focus:ring-brand-500"
                                    />
                                    <span>{tag.name}</span>
                                  </label>
                                );
                              })}
                            </div>
                          ) : (
                            <span className="text-slate-500">
                              No tags yet. Manage tags under Settings → Tags.
                            </span>
                          )}
                        </div>

                        {capability?.functions && capability.functions.length ? (
                          <div className="mt-2 flex flex-wrap gap-1">
                            {capability.functions.slice(0, 10).map((fn) => (
                              <span
                                key={fn}
                                className="inline-flex items-center rounded-full bg-white px-2 py-0.5 text-xs font-medium text-slate-600 ring-1 ring-slate-200"
                              >
                                {fn}
                              </span>
                            ))}
                            {capability.functions.length > 10 ? (
                              <span className="text-xs text-slate-500">+{capability.functions.length - 10} more</span>
                            ) : null}
                          </div>
                        ) : null}
                      </div>
                    );
                  })}
                </div>
              </div>
            </section>
          </div>

          <footer className="flex items-center justify-between border-t border-slate-200 px-6 py-4">
            {errorMessage ? <p className="text-sm text-rose-600">{errorMessage}</p> : <span />}
            <div className="flex gap-2">
              <button
                type="button"
                onClick={handleDelete}
                disabled={deleteMutation.isPending}
                className="inline-flex items-center rounded-md border border-rose-200 bg-white px-4 py-2 text-sm font-medium text-rose-600 shadow-sm transition hover:bg-rose-50 disabled:cursor-not-allowed disabled:border-rose-100 disabled:text-rose-300"
              >
                {deleteMutation.isPending ? 'Removing…' : 'Remove controller'}
              </button>
              <button
                type="button"
                onClick={onClose}
                className="inline-flex items-center rounded-md border border-slate-300 bg-white px-4 py-2 text-sm font-medium text-slate-700 shadow-sm transition hover:bg-slate-50"
              >
                Cancel
              </button>
              <button
                type="submit"
                disabled={mutation.isPending}
                className="inline-flex items-center rounded-md bg-brand-500 px-4 py-2 text-sm font-medium text-white shadow-sm transition hover:bg-brand-600 disabled:cursor-not-allowed disabled:bg-brand-300"
              >
                {mutation.isPending ? 'Saving…' : 'Save changes'}
              </button>
            </div>
          </footer>
        </form>
      </div>
    </div>
  );
};

const DiscoveryControllerModal = ({ discovered, open, onClose, onSaved }: DiscoveredModalProps) => {
  const connectMutation = useConnectDiscoveredDevice();
  const { data: settings } = useApplicationSettings(true);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);
  const [apiKeyInput, setApiKeyInput] = useState('');
  const [deviceName, setDeviceName] = useState('');

  useEffect(() => {
    if (!open) return;
    setErrorMessage(null);
    setApiKeyInput('');
    setDeviceName(discovered.friendly_name || '');
  }, [open, discovered]);

  const capabilitiesObject = useMemo(() => extractDiscoveryCapabilities(discovered), [discovered]);
  const brandSummary = useMemo(() => extractBrands(capabilitiesObject), [capabilitiesObject]);
  const portCapabilities = useMemo(() => extractPortCapabilities(capabilitiesObject), [capabilitiesObject]);
  const portEntries = useMemo(() => Array.from(portCapabilities.entries()).sort((a, b) => a[0] - b[0]), [portCapabilities]);

  const metadata = discovered.discovery_properties && typeof discovered.discovery_properties === 'object'
    ? (discovered.discovery_properties as Record<string, unknown>)
    : {};
  const firmware = typeof metadata.firmware_version === 'string' ? metadata.firmware_version : discovered.firmware_version;
  const projectName = typeof metadata.project_name === 'string' ? metadata.project_name : undefined;
  const projectVersion = typeof metadata.project_version === 'string' ? metadata.project_version : undefined;
  const network = typeof metadata.network === 'string' ? metadata.network : 'wifi';
  const boardInfo = typeof metadata.board === 'string' ? metadata.board : 'Unknown';
  const platformInfo = typeof metadata.platform === 'string' ? metadata.platform : 'Unknown';
  const globalApiKey =
    settings && typeof settings['esphome_api_key']?.value === 'string'
      ? (settings['esphome_api_key'].value as string)
      : '';

  const handleConnect = async () => {
    setErrorMessage(null);
    try {
      const payload: Record<string, unknown> = {};
      const apiKeyClean = apiKeyInput.trim();
      if (apiKeyClean) {
        payload['api_key'] = apiKeyClean;
      }
      const deviceNameClean = deviceName.trim();
      if (deviceNameClean) {
        payload['device_name'] = deviceNameClean;
      }
      await connectMutation.mutateAsync({ hostname: discovered.hostname, payload });
      if (onSaved) {
        onSaved();
      } else {
        onClose();
      }
    } catch (error) {
      const message = error instanceof Error ? error.message : 'Failed to connect controller.';
      setErrorMessage(message);
    }
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center">
      <div className="absolute inset-0 bg-slate-900/40" aria-hidden="true" onClick={onClose} />
      <div
        role="dialog"
        aria-modal="true"
        className="relative z-10 h-[85vh] w-full max-w-3xl overflow-hidden rounded-xl bg-white shadow-xl"
      >
        <div className="flex h-full flex-col">
          <header className="border-b border-slate-200 px-6 py-4">
            <h3 className="text-lg font-semibold text-slate-900">Connect controller</h3>
            <p className="text-sm text-slate-500">Hostname {discovered.hostname}</p>
            <p className="text-xs text-slate-500">IP {discovered.ip_address} • MAC {discovered.mac_address.toUpperCase()}</p>
            {firmware ? <p className="text-xs text-slate-500">Firmware {firmware}</p> : null}
            {projectName ? (
              <p className="text-xs text-slate-500">Project {projectName}{projectVersion ? ` (${projectVersion})` : ''}</p>
            ) : null}
            {brandSummary.length ? (
              <p className="mt-2 text-xs text-slate-500">Capabilities: {brandSummary.join(', ')}</p>
            ) : null}
          </header>

          <div className="flex-1 overflow-y-auto px-6 py-4">
            <section className="space-y-4">
              <div className="rounded-lg border border-slate-200 bg-slate-50/60 px-4 py-3">
                <p className="text-sm font-semibold text-slate-900">Controller details</p>
                <dl className="mt-2 grid grid-cols-1 gap-3 text-sm text-slate-600 sm:grid-cols-2">
                  <div>
                    <dt className="text-xs uppercase text-slate-500">Friendly name</dt>
                    <dd>{discovered.friendly_name ?? '—'}</dd>
                  </div>
                  <div>
                    <dt className="text-xs uppercase text-slate-500">Network</dt>
                    <dd>{network}</dd>
                  </div>
                  <div>
                    <dt className="text-xs uppercase text-slate-500">Board</dt>
                    <dd>{boardInfo}</dd>
                  </div>
                  <div>
                    <dt className="text-xs uppercase text-slate-500">Platform</dt>
                    <dd>{platformInfo}</dd>
                  </div>
                </dl>
              </div>

              <label className="flex flex-col text-sm font-medium text-slate-700">
                Controller name
                <input
                  type="text"
                  value={deviceName}
                  onChange={(event) => setDeviceName(event.target.value)}
                  placeholder="Enter a name for this controller"
                  className="mt-1 rounded-md border border-slate-300 px-3 py-2 text-sm text-slate-900 shadow-sm focus:border-brand-500 focus:outline-none focus:ring-1 focus:ring-brand-500"
                />
                <span className="mt-1 text-xs text-slate-500">
                  Give this controller a friendly name (e.g., "Office TV", "Lobby IR Controller")
                </span>
              </label>

              <label className="flex flex-col text-sm font-medium text-slate-700">
                API key
                <input
                  type="text"
                  value={apiKeyInput}
                  onChange={(event) => setApiKeyInput(event.target.value)}
                  placeholder={globalApiKey ? `${globalApiKey} (application key)` : 'Uses application key'}
                  className="mt-1 rounded-md border border-slate-300 px-3 py-2 text-sm text-slate-900 shadow-sm focus:border-brand-500 focus:outline-none focus:ring-1 focus:ring-brand-500"
                />
                <span className="mt-1 text-xs text-slate-500">
                  Leave blank to use the application API key when connecting this controller.
                </span>
              </label>

              {portEntries.length ? (
                <div className="space-y-3">
                  <h4 className="text-sm font-semibold text-slate-900">Detected ports</h4>
                  <div className="space-y-3">
                    {portEntries.map(([portNumber, capability]) => (
                      <div key={portNumber} className="rounded-lg border border-slate-200 bg-white px-4 py-3 shadow-sm">
                        <div className="flex items-center justify-between">
                          <p className="text-sm font-semibold text-slate-900">Port {portNumber}</p>
                          {capability.brand ? (
                            <span className="text-xs text-slate-500">{capability.brand}</span>
                          ) : null}
                        </div>
                        {capability.description ? (
                          <p className="mt-1 text-xs text-slate-500">{capability.description}</p>
                        ) : null}
                        {capability.functions && capability.functions.length ? (
                          <div className="mt-2 flex flex-wrap gap-1">
                            {capability.functions.slice(0, 10).map((fn) => (
                              <span
                                key={fn}
                                className="inline-flex items-center rounded-full bg-slate-50 px-2 py-0.5 text-xs font-medium text-slate-600 ring-1 ring-slate-200"
                              >
                                {fn}
                              </span>
                            ))}
                            {capability.functions.length > 10 ? (
                              <span className="text-xs text-slate-500">+{capability.functions.length - 10} more</span>
                            ) : null}
                          </div>
                        ) : null}
                      </div>
                    ))}
                  </div>
                </div>
              ) : (
                <p className="text-sm text-slate-500">No port capabilities reported yet.</p>
              )}
            </section>
          </div>

          <footer className="flex items-center justify-between border-t border-slate-200 px-6 py-4">
            {errorMessage ? <p className="text-sm text-rose-600">{errorMessage}</p> : <span />}
            <div className="flex gap-2">
              <button
                type="button"
                onClick={onClose}
                className="inline-flex items-center rounded-md border border-slate-300 bg-white px-4 py-2 text-sm font-medium text-slate-700 shadow-sm transition hover:bg-slate-50"
              >
                Cancel
              </button>
              <button
                type="button"
                onClick={handleConnect}
                disabled={connectMutation.isPending}
                className="inline-flex items-center rounded-md bg-brand-500 px-4 py-2 text-sm font-medium text-white shadow-sm transition hover:bg-brand-600 disabled:cursor-not-allowed disabled:bg-brand-300"
              >
                {connectMutation.isPending ? 'Connecting…' : 'Connect'}
              </button>
            </div>
          </footer>
        </div>
      </div>
    </div>
  );
};

// Inline version for port header
const PortAvailableCommandsInline = ({ libraryId }: { libraryId?: number }) => {
  const [isExpanded, setIsExpanded] = useState(false);
  const { data: libraryCommands, isLoading } = useLibraryCommands(libraryId);

  if (!libraryId || isLoading || !libraryCommands || !libraryCommands.commands.length) {
    return null;
  }

  const { library, commands } = libraryCommands;
  const libraryName = library.brand && library.model
    ? `${library.brand} ${library.model}`
    : library.brand || library.model || library.name;

  return (
    <div className="relative">
      <button
        type="button"
        onClick={() => setIsExpanded(!isExpanded)}
        className="rounded-md border border-slate-300 bg-white px-2 py-1 text-xs font-medium text-slate-700 shadow-sm hover:bg-slate-50"
      >
        Commands ({commands.length})
      </button>

      {isExpanded ? (
        <div className="absolute right-0 top-full z-10 mt-1 w-80 rounded-md border border-slate-200 bg-white shadow-lg">
          <div className="border-b border-slate-200 px-3 py-2">
            <p className="text-xs font-medium text-slate-700">
              {libraryName}
            </p>
          </div>
          <div className="max-h-60 overflow-y-auto px-3 py-2">
            <div className="space-y-1">
              {commands.map((cmd) => (
                <div
                  key={cmd.id}
                  className="flex items-center justify-between rounded px-2 py-1 text-xs hover:bg-slate-50"
                >
                  <span className="font-medium text-slate-700">
                    {cmd.display_name || cmd.name}
                  </span>
                  <span className="text-slate-500">
                    {cmd.name}
                  </span>
                </div>
              ))}
            </div>
          </div>
          <div className="border-t border-slate-200 px-3 py-2">
            <button
              type="button"
              onClick={() => setIsExpanded(false)}
              className="text-xs text-slate-600 hover:text-slate-900"
            >
              Close
            </button>
          </div>
        </div>
      ) : null}
    </div>
  );
};

const _PortAvailableCommands = ({ libraryId }: { libraryId?: number }) => {
  const [isExpanded, setIsExpanded] = useState(false);
  const { data: libraryCommands, isLoading } = useLibraryCommands(libraryId);

  if (!libraryId) {
    return null;
  }

  if (isLoading) {
    return (
      <div className="mt-2 text-xs text-slate-500">
        Loading available commands...
      </div>
    );
  }

  if (!libraryCommands || !libraryCommands.commands.length) {
    return null;
  }

  const { library, commands } = libraryCommands;
  const libraryName = library.brand && library.model
    ? `${library.brand} ${library.model}`
    : library.brand || library.model || library.name;

  return (
    <div className="mt-2 rounded-md border border-slate-200 bg-white">
      <button
        type="button"
        onClick={() => setIsExpanded(!isExpanded)}
        className="flex w-full items-center justify-between px-3 py-2 text-left text-xs font-medium text-slate-700 hover:bg-slate-50"
      >
        <span>
          Available Commands ({commands.length}) - {libraryName}
        </span>
        <span className="text-slate-400">
          {isExpanded ? '▼' : '▶'}
        </span>
      </button>

      {isExpanded ? (
        <div className="border-t border-slate-200 px-3 py-2">
          <div className="max-h-60 overflow-y-auto">
            <div className="space-y-1">
              {commands.map((cmd) => (
                <div
                  key={cmd.id}
                  className="flex items-center justify-between rounded px-2 py-1 text-xs hover:bg-slate-50"
                >
                  <span className="font-medium text-slate-700">
                    {cmd.display_name || cmd.name}
                  </span>
                  <div className="flex items-center gap-2">
                    {cmd.category ? (
                      <span className="rounded-full bg-slate-100 px-2 py-0.5 text-xs text-slate-600">
                        {cmd.category}
                      </span>
                    ) : null}
                    <span className="text-slate-500">{cmd.protocol}</span>
                  </div>
                </div>
              ))}
            </div>
          </div>
        </div>
      ) : null}
    </div>
  );
};

type DefaultChannelSource = 'none' | 'option' | 'custom';

interface PortFormState {
  port_number: number;
  connected_device_name: string;
  is_active: boolean;
  cable_length: string | null;
  installation_notes: string | null;
  tag_ids: number[];
  default_channel: string | null;
  default_channel_source: DefaultChannelSource;
  device_number: number | null;
}

interface PortCapabilitySnapshot {
  brand?: string;
  description?: string;
  functions?: string[];
  lib?: number;
}

const sanitizeValue = (value: string) => (value.trim().length ? value.trim() : null);

function formatChannelLabel(channel: ChannelOption): string {
  const details: string[] = [];
  if (channel.lcn) {
    details.push(`LCN ${channel.lcn}`);
  }
  if (channel.foxtel_number) {
    details.push(`Foxtel ${channel.foxtel_number}`);
  }
  return details.length ? `${channel.channel_name} (${details.join(' · ')})` : channel.channel_name;
}

function normalizeDefaultChannel(value: string | null): string | null {
  if (!value) return null;
  const trimmed = value.trim();
  return trimmed.length ? trimmed : null;
}

function resolveDefaultChannelSource(value: string | null): DefaultChannelSource {
  if (!value) return 'none';
  // Treat all non-empty values as custom initially
  // The UI will detect if it matches an option and adjust accordingly
  return 'custom';
}

function resolveChannelSelectValue(port: PortFormState, options: Array<{ value: string }>): string {
  if (port.default_channel_source === 'none') {
    return '';
  }

  // Check if the current value matches any option (regardless of source)
  if (port.default_channel && options.some((option) => option.value === port.default_channel)) {
    return port.default_channel;
  }

  if (port.default_channel_source === 'option') {
    return port.default_channel ?? '';
  }

  return '__custom__';
}

function mapPorts(ports: IRPort[]): PortFormState[] {
  return ports
    .slice()
    .sort((a, b) => a.port_number - b.port_number)
    .map((port) => ({
      port_number: port.port_number,
      connected_device_name: port.connected_device_name ?? '',
      is_active: port.is_active,
      cable_length: port.cable_length ?? null,
      installation_notes: port.installation_notes ?? null,
      tag_ids: port.tag_ids ?? [],
      default_channel: normalizeDefaultChannel(port.default_channel),
      default_channel_source: resolveDefaultChannelSource(normalizeDefaultChannel(port.default_channel)),
      device_number: port.device_number ?? null,
    }));
}

function extractDiscoveryCapabilities(discovered: DiscoveredDevice): unknown {
  const properties = discovered.discovery_properties;
  if (!properties || typeof properties !== 'object') {
    return null;
  }
  const record = properties as Record<string, unknown>;
  if ('capabilities' in record) {
    return record.capabilities;
  }
  return null;
}

function extractPortCapabilities(capabilities: unknown) {
  const map = new Map<number, PortCapabilitySnapshot>();
  if (!capabilities || typeof capabilities !== 'object') {
    return map;
  }
  const record = capabilities as Record<string, unknown>;
  const ports = record.ports;
  if (!Array.isArray(ports)) {
    return map;
  }
  ports.forEach((entry) => {
    if (!entry || typeof entry !== 'object') return;
    const item = entry as Record<string, unknown>;
    const rawPort = item.port ?? item.port_number;
    const portNumber = typeof rawPort === 'number' ? rawPort : Number(rawPort);
    if (!Number.isFinite(portNumber)) return;
    const functions = Array.isArray(item.functions)
      ? (item.functions as unknown[]).filter((value): value is string => typeof value === 'string')
      : undefined;
    const lib = typeof item.lib === 'number' ? item.lib : undefined;
    map.set(portNumber, {
      brand: typeof item.brand === 'string' ? item.brand : undefined,
      description: typeof item.description === 'string' ? item.description : undefined,
      functions,
      lib,
    });
  });
  return map;
}

function extractBrands(capabilities: unknown) {
  if (!capabilities || typeof capabilities !== 'object') {
    return [] as string[];
  }
  const record = capabilities as Record<string, unknown>;
  const brands = record.brands;
  if (Array.isArray(brands)) {
    return brands.filter((value): value is string => typeof value === 'string');
  }
  return [];
}
