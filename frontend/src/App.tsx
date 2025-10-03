import React, { useState, useEffect, useCallback, useRef } from 'react';
import './index.css';
import type {
  Page,
  SettingsTab,
  ChannelTab,
  DiscoveredDevice,
  ManagedDevice,
  DeviceTag,
  Channel,
  ChannelStats,
  AreaInfo,
  InHouseChannelCreate,
  InHouseChannelUpdate,
  IRPort,
  IRPortConfigUpdate,
  TemplateLibraryItem,
  RawTemplateCategory,
  TemplateCategory,
  SelectedLibrary,
  ManagedDeviceUpdateRequest,
  ConnectedDevice,
  TemplateSummary,
  ESPTemplateResponse
} from './types';
import {
  copyTextToClipboard,
  getApiErrorMessage,
  extractSubstitutionValue,
  updateYamlSubstitution,
  ensureWifiHiddenBinding,
  ensureProjectName,
  ensureJsonInclude,
  normalizeCapabilitiesLambda,
  normalizeTemplateYaml
} from './utils';
import { useDevices, useChannels, useTemplates, useTags } from './hooks';
import ErrorBoundary from './components/ErrorBoundary';
import LoadingSpinner from './components/LoadingSpinner';
import ErrorMessage from './components/ErrorMessage';
import DevicesPage from './pages/DevicesPage';
import IRSendersPage from './pages/IRSendersPage';
import YamlBuilderPage from './pages/YamlBuilderPage';
import IRPortConfig from './components/IRPortConfig';

function App() {
  // Custom hooks for data management
  const devicesHook = useDevices();
  const channelsHook = useChannels();
  const templatesHook = useTemplates();
  const tagsHook = useTags();

  const [discoveredDevices, setDiscoveredDevices] = useState<DiscoveredDevice[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [editingDevice, setEditingDevice] = useState<ManagedDevice | null>(null);
  const [showIRConfig, setShowIRConfig] = useState<ManagedDevice | null>(null);
  const [portConfigs, setPortConfigs] = useState<Record<number, IRPortConfigUpdate>>({});

  // YAML builder state
  const [templateId, setTemplateId] = useState<number | null>(null);
  const [baseTemplate, setBaseTemplate] = useState<string>('');
  const [yamlPreview, setYamlPreview] = useState<string>('');
  const [yamlCharCount, setYamlCharCount] = useState<number>(0);
  const [includeComments, setIncludeComments] = useState<boolean>(true);
  const [templateCategories, setTemplateCategories] = useState<TemplateCategory[]>([]);
  const [selectedLibraries, setSelectedLibraries] = useState<SelectedLibrary[]>([]);
  const [portAssignments, setPortAssignments] = useState<(number | null)[]>([null, null, null, null, null]);
  const [builderInitialized, setBuilderInitialized] = useState(false);
  const [builderLoading, setBuilderLoading] = useState(false);
  const [builderError, setBuilderError] = useState<string | null>(null);
  const [previewLoading, setPreviewLoading] = useState(false);
  const [compileLoading, setCompileLoading] = useState(false);
  const [compileOutput, setCompileOutput] = useState<string | null>(null);
  const [downloadUrl, setDownloadUrl] = useState<string | null>(null);
  const [binaryFilename, setBinaryFilename] = useState<string | null>(null);
  const compileOutputRef = useRef<HTMLPreElement>(null);

  // Navigation state
  const [currentPage, setCurrentPage] = useState<Page>('devices');
  const [selectedDevice, setSelectedDevice] = useState<string | null>(null);
  const [settingsTab, setSettingsTab] = useState<SettingsTab>('yaml-templates');
  const [channelTab, setChannelTab] = useState<ChannelTab>('area-selection');
  const [sortField, setSortField] = useState<keyof ConnectedDevice>('name');
  const [sortDirection, setSortDirection] = useState<'asc' | 'desc'>('asc');
  const [filters, setFilters] = useState<{[key: string]: string}>({});

  const [selectedDevices, setSelectedDevices] = useState<Set<string>>(new Set());
  const [expandedDevice, setExpandedDevice] = useState<string | null>(null);

  // Other channel related state not covered by hooks
  const [channelStats, setChannelStats] = useState<ChannelStats | null>(null);
  const [channelFilters, setChannelFilters] = useState<{
    platform?: string;
    broadcaster?: string;
    search?: string;
    enabled_only: boolean;
  }>({ enabled_only: false });
  const [showInhouseModal, setShowInhouseModal] = useState(false);
  const [selectedArea, setSelectedArea] = useState<string>('');
  const [selectedCity, setSelectedCity] = useState<string>('');
  const [settingsTemplateDirty, setSettingsTemplateDirty] = useState(false);
  const [templateFeedbackMessage, setTemplateFeedbackMessage] = useState<string | null>(null);
  const [versionIncrement, setVersionIncrement] = useState<'major' | 'minor' | 'patch'>('patch');
  const [testCompile, setTestCompile] = useState(false);
  const [apiKey, setApiKey] = useState('');
  const [apiKeyEditable, setApiKeyEditable] = useState(false);
  const [otaEditable, setOtaEditable] = useState(false);

  // IR Config modal location state
  const [configLocation, setConfigLocation] = useState<string>('');
  const [locationMode, setLocationMode] = useState<'existing' | 'custom'>('existing');

  const API_BASE = '/api/v1/management';
  const TEMPLATE_API_BASE = '/api/v1/templates';
  const SETTINGS_API_BASE = '/api/v1/settings';
  const CHANNELS_API_BASE = '/api/v1/channels';
  const STATIC_BASE_URL = import.meta.env.VITE_BACKEND_URL || 'http://localhost:8000';




  // Template save functionality handled by templates hook

  // Generate connected devices from managed devices and their ports
  const connectedDevices = React.useMemo<ConnectedDevice[]>(() => {
    const devices: ConnectedDevice[] = [];

    devicesHook.devices.forEach(sender => {
      sender.ir_ports?.forEach(port => {
        if (port.is_active) {
          // Get tags for this port
          const portTags = port.tag_ids?.map(tagId =>
            tagsHook.deviceTags.find(tag => tag.id === tagId)
          ).filter(Boolean) as DeviceTag[] || [];

          devices.push({
            id: `${sender.id}-${port.port_number}`,
            name: port.connected_device_name || `Port ${port.port_number}`,
            type: sender.device_type || 'IR Device',
            location: sender.location || 'Not set',
            ir_sender: sender.device_name || sender.hostname,
            port: port.port_id || `Port ${port.port_number}`,
            status: sender.is_online ? 'online' : 'offline',
            last_used: sender.last_seen,
            channels: port.device_number ? [`Device ${port.device_number}`] : [],
            tags: portTags
          });
        }
      });
    });

    return devices;
  }, [devicesHook.devices, tagsHook.deviceTags]);

  const resetPreviewAssignments = (assignments: (number | null)[]) => {
    const payload = assignments.map((libraryId, index) => ({
      port_number: index + 1,
      library_id: libraryId,
    }));
    return payload;
  };

  const handleSelectLibrary = (library: TemplateLibraryItem) => {
    setBuilderError(null);
    setSelectedLibraries((prev) => {
      if (prev.find((item) => item.id === library.id)) {
        return prev;
      }
      if (prev.length >= 2) {
        setBuilderError('You can select up to two devices for now.');
        return prev;
      }
      const updated = [...prev, {
        id: library.id,
        name: library.name,
        device_category: library.device_category,
        brand: library.brand,
        model: library.model,
        source_path: library.source_path,
        espNative: library.espNative,
      }];

      setPortAssignments((ports) => {
        const next = [...ports];
        const openIndex = next.findIndex((value) => value === null);
        if (openIndex !== -1) {
          next[openIndex] = library.id;
        }
        return next;
      });

      return updated;
    });
  };

  const handleRemoveLibrary = (libraryId: number) => {
    setBuilderError(null);
    setSelectedLibraries((prev) => prev.filter((item) => item.id !== libraryId));
    setPortAssignments((ports) => ports.map((value) => (value === libraryId ? null : value)));
  };

  const handlePortAssignmentChange = (index: number, value: string) => {
    const parsed = value === '' ? null : Number(value);
    setPortAssignments((ports) => {
      const next = [...ports];
      next[index] = Number.isNaN(parsed) ? null : parsed;
      return next;
    });
  };

  const handleCompile = useCallback(async () => {
    const yaml = (yamlPreview || baseTemplate || '').trim();
    if (!yaml) {
      setCompileOutput('No YAML available to compile.');
      return;
    }

    try {
      setCompileLoading(true);
      setCompileOutput('Starting compilation...\n');
      setDownloadUrl(null);
      setBinaryFilename(null);
      setBuilderError(null);

      const response = await fetch(`${TEMPLATE_API_BASE}/compile-stream`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ yaml }),
      });

      if (!response.ok) {
        throw new Error(`HTTP ${response.status}: ${response.statusText}`);
      }

      const reader = response.body?.getReader();
      if (!reader) {
        throw new Error('Response body is not readable');
      }

      const decoder = new TextDecoder();
      let buffer = '';

      while (true) {
        const { done, value } = await reader.read();
        if (done) break;

        buffer += decoder.decode(value, { stream: true });

        // Process complete lines
        let newlineIndex;
        while ((newlineIndex = buffer.indexOf('\n')) !== -1) {
          const line = buffer.slice(0, newlineIndex);
          buffer = buffer.slice(newlineIndex + 1);

          if (line.startsWith('data: ')) {
            try {
              const data = JSON.parse(line.slice(6));

              if (data.type === 'output') {
                setCompileOutput(prev => {
                  const newOutput = prev + data.message + '\n';
                  // Auto-scroll to bottom
                  setTimeout(() => {
                    if (compileOutputRef.current) {
                      compileOutputRef.current.scrollTop = compileOutputRef.current.scrollHeight;
                    }
                  }, 0);
                  return newOutput;
                });
              } else if (data.type === 'complete') {
                if (data.success && data.binary_filename) {
                  setDownloadUrl(`${TEMPLATE_API_BASE}/download/${data.binary_filename}`);
                  setBinaryFilename(data.binary_filename);
                  setCompileOutput(prev => prev + '\n✅ Compilation successful! Binary ready for download.\n');
                } else {
                  setBuilderError('ESPHome compilation failed. See output for details.');
                }
              } else if (data.type === 'error') {
                setBuilderError(data.message);
                setCompileOutput(prev => prev + '\n❌ ' + data.message + '\n');
              } else if (data.type === 'status') {
                setCompileOutput(prev => prev + data.message + '\n');
              } else if (data.type === 'keepalive') {
                // Ignore keepalive messages
              }
            } catch (e) {
              console.warn('Failed to parse SSE data:', line);
            }
          }
        }
      }

    } catch (err) {
      console.error('Compilation error:', err);
      setCompileOutput(getApiErrorMessage(err, 'Compilation request failed.'));
      setBuilderError('Compilation request failed.');
    } finally {
      setCompileLoading(false);
    }
  }, [TEMPLATE_API_BASE, yamlPreview, baseTemplate]);

  const handleSaveYaml = useCallback(() => {
    const yaml = (yamlPreview || baseTemplate || '').trim();
    if (!yaml) {
      setBuilderError('No YAML available to save.');
      return;
    }

    const timestamp = new Date().toISOString().replace(/[:.]/g, '-').slice(0, 19);
    const filename = `smartvenue-ir-${timestamp}.yaml`;

    const blob = new Blob([yaml], { type: 'text/yaml' });
    const url = URL.createObjectURL(blob);

    const link = document.createElement('a');
    link.href = url;
    link.download = filename;
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
    URL.revokeObjectURL(url);

    setBuilderError(null);
  }, [yamlPreview, baseTemplate]);

  const handleSaveYamlToServer = useCallback(async () => {
    const yaml = (yamlPreview || baseTemplate || '').trim();
    if (!yaml) {
      setBuilderError('No YAML available to save.');
      return;
    }

    try {
      const response = await fetch(`${TEMPLATE_API_BASE}/save-yaml`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({ yaml }),
      });

      if (!response.ok) {
        throw new Error('Failed to save YAML to server');
      }

      const data = await response.json();
      setBuilderError(`✅ YAML saved to server: ${data.filename}`);
    } catch (err) {
      console.error(err);
      setBuilderError(getApiErrorMessage(err, 'Failed to save YAML to server.'));
    }
  }, [TEMPLATE_API_BASE, yamlPreview, baseTemplate]);

  const requestPreview = useCallback(
    async (
      templateIdOverride?: number,
      assignmentsOverride?: (number | null)[],
      includeCommentsOverride?: boolean
    ) => {
      const effectiveTemplateId = templateIdOverride ?? templateId;
      if (!effectiveTemplateId) {
        return;
      }

      const assignments = assignmentsOverride ?? portAssignments;
      const include = includeCommentsOverride ?? includeComments;

      const body = {
        template_id: effectiveTemplateId,
        assignments: resetPreviewAssignments(assignments),
        include_comments: include,
      };

      try {
        setPreviewLoading(true);
        const response = await fetch(`${TEMPLATE_API_BASE}/preview`, {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json',
          },
          body: JSON.stringify(body),
        });

        if (!response.ok) {
          throw new Error('Failed to generate YAML preview');
        }

        const data = await response.json();
        setYamlPreview(data.yaml);
        setYamlCharCount(data.char_count);
      } catch (err) {
        console.error(err);
        setBuilderError(getApiErrorMessage(err, 'Unable to generate YAML preview.'));
      } finally {
        setPreviewLoading(false);
      }
    },
    [templateId, portAssignments, includeComments, TEMPLATE_API_BASE]
  );

  const fetchBuilderData = useCallback(async (force = false) => {
    if (builderInitialized && !force) {
      return;
    }

    setBuilderLoading(true);
    setBuilderError(null);

    try {
      const [templateRes, hierarchyRes] = await Promise.all([
        fetch(`${TEMPLATE_API_BASE}/base`),
        fetch(`${TEMPLATE_API_BASE}/device-hierarchy`),
      ]);

      if (!templateRes.ok) {
        throw new Error('Failed to load base template');
      }
      if (!hierarchyRes.ok) {
        throw new Error('Failed to load device hierarchy');
      }

      const templateData = await templateRes.json();
      const hierarchyData: RawTemplateCategory[] = await hierarchyRes.json();

      const normalizedCategories: TemplateCategory[] = hierarchyData.map((category) => {
        const displayName = category.name.toLowerCase().startsWith('tv')
          ? ` ${category.name}`
          : category.name;

        return {
          name: displayName,
          brands: category.brands.map((brand) => ({
            name: brand.name,
            libraries: brand.libraries.map((library) => ({
              id: library.id,
              name: library.name,
              device_category: library.device_category,
              brand: library.brand,
              model: library.model ?? undefined,
              source_path: library.source_path,
              espNative: Boolean(library.esp_native),
            })),
          })),
        };
      });

      const nativeIndex = normalizedCategories.findIndex((category) => category.brands.some((brand) => brand.libraries.some((library) => library.espNative)));
      if (nativeIndex > 0) {
        const [nativeCategory] = normalizedCategories.splice(nativeIndex, 1);
        normalizedCategories.unshift(nativeCategory);
      }

      setTemplateId(templateData.id);
      setBaseTemplate(templateData.template_yaml);
      setTemplateCategories(normalizedCategories);
      setBuilderInitialized(true);

      await requestPreview(templateData.id, portAssignments, includeComments);
    } catch (err) {
      console.error(err);
      setBuilderError(getApiErrorMessage(err, 'Failed to initialize YAML builder.'));
    } finally {
      setBuilderLoading(false);
    }
  }, [builderInitialized, includeComments, portAssignments, requestPreview, TEMPLATE_API_BASE]);

  useEffect(() => {
    if (!templateFeedbackMessage) {
      return;
    }
    const timeout = window.setTimeout(() => setTemplateFeedbackMessage(null), 2000);
    return () => window.clearTimeout(timeout);
  }, [templateFeedbackMessage]);

  // Handle port configuration data changes
  const handlePortDataChange = (portNumber: number, data: IRPortConfigUpdate) => {
    setPortConfigs(prev => ({
      ...prev,
      [portNumber]: data
    }));
  };

  // Save IR configuration
  const saveIRConfiguration = async () => {
    if (!showIRConfig) return;

    try {
      const portData: IRPortConfigUpdate[] = Object.values(portConfigs);

      const response = await fetch(`${API_BASE}/managed/${showIRConfig.id}`, {
        method: 'PUT',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          location: configLocation || null,
          ir_ports: portData
        }),
      });

      if (response.ok) {
        setShowIRConfig(null);
        setPortConfigs({});
        setConfigLocation('');
        await devicesHook.fetchDevices();
        await fetchDiscoveredDevices();
      } else {
        throw new Error('Failed to save configuration');
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to save configuration');
    }
  };

  // Tag management functions

  const createDeviceTag = async (name: string, color?: string, description?: string) => {
    try {
      const response = await fetch(`${SETTINGS_API_BASE}/tags`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ name, color, description })
      });

      if (response.ok) {
        await tagsHook.fetchTags();
        return true;
      } else {
        const errorData = await response.json();
        setError(errorData.detail || 'Failed to create tag');
        return false;
      }
    } catch (error) {
      console.error('Failed to create tag:', error);
      setError('Failed to create tag');
      return false;
    }
  };

  const updateDeviceTag = async (tagId: number, name: string, color?: string, description?: string) => {
    try {
      const response = await fetch(`${SETTINGS_API_BASE}/tags/${tagId}`, {
        method: 'PUT',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ name, color, description })
      });

      if (response.ok) {
        await tagsHook.fetchTags();
        return true;
      } else {
        const errorData = await response.json();
        setError(errorData.detail || 'Failed to update tag');
        return false;
      }
    } catch (error) {
      console.error('Failed to update tag:', error);
      setError('Failed to update tag');
      return false;
    }
  };

  const deleteDeviceTag = async (tagId: number) => {
    try {
      const response = await fetch(`${SETTINGS_API_BASE}/tags/${tagId}`, {
        method: 'DELETE'
      });

      if (response.ok) {
        await tagsHook.fetchTags();
        await devicesHook.fetchDevices(); // Refresh device data to update tag associations
        return true;
      } else {
        const errorData = await response.json();
        setError(errorData.detail || 'Failed to delete tag');
        return false;
      }
    } catch (error) {
      console.error('Failed to delete tag:', error);
      setError('Failed to delete tag');
      return false;
    }
  };

  // Channels management functions
  const fetchChannels = async () => {
    // Channels loading handled by hook(true);
    try {
      const params = new URLSearchParams();
      if (channelFilters.platform) params.append('platform', channelFilters.platform);
      if (channelFilters.broadcaster) params.append('broadcaster', channelFilters.broadcaster);
      if (channelFilters.search) params.append('search', channelFilters.search);
      if (channelFilters.enabled_only) params.append('enabled_only', 'true');
      params.append('limit', '500');

      const response = await fetch(`${CHANNELS_API_BASE}/channels?${params}`);
      if (response.ok) {
        const channelsData = await response.json();
        channelsHook.setChannels(channelsData);
      } else {
        setError('Failed to fetch channels');
      }
    } catch (error) {
      console.error('Failed to fetch channels:', error);
      setError('Failed to fetch channels');
    } finally {
      // Channels loading handled by hook(false);
    }
  };

  const fetchChannelsForArea = async (areaName: string) => {
    // Channels loading handled by hook(true);
    try {
      // Fetch all channels and filter by area availability
      const params = new URLSearchParams();
      params.append('limit', '500');

      const response = await fetch(`${CHANNELS_API_BASE}/channels?${params}`);
      if (response.ok) {
        const allChannels = await response.json();
        // Filter channels that are available in the selected area
        const areaChannels = allChannels.filter((channel: any) =>
          channel.availability && channel.availability.includes(areaName)
        );
        channelsHook.setChannels(areaChannels);

        // Set channelsHook.selectedChannels to currently enabled channels for this area
        const enabledChannelIds = areaChannels
          .filter((channel: any) => !channel.disabled)
          .map((channel: any) => channel.id);
        channelsHook.setSelectedChannels(new Set(enabledChannelIds));
      } else {
        setError('Failed to fetch channels for area');
      }
    } catch (error) {
      console.error('Failed to fetch channels for area:', error);
      setError('Failed to fetch channels for area');
    } finally {
      // Channels loading handled by hook(false);
    }
  };

  const fetchChannelStats = async () => {
    try {
      const response = await fetch(`${CHANNELS_API_BASE}/channels/stats`);
      if (response.ok) {
        const stats = await response.json();
        setChannelStats(stats);
      }
    } catch (error) {
      console.error('Failed to fetch channel stats:', error);
    }
  };

  const updateChannel = async (channelId: number, updates: { disabled?: boolean; internal?: boolean }) => {
    try {
      const response = await fetch(`${CHANNELS_API_BASE}/channels/${channelId}`, {
        method: 'PATCH',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(updates)
      });

      if (response.ok) {
        await fetchChannels();
        await fetchChannelStats();
        return true;
      } else {
        const errorData = await response.json();
        setError(errorData.detail || 'Failed to update channel');
        return false;
      }
    } catch (error) {
      console.error('Failed to update channel:', error);
      setError('Failed to update channel');
      return false;
    }
  };

  const bulkUpdateChannels = async (channelIds: number[], updates: { disabled?: boolean; internal?: boolean }) => {
    try {
      const response = await fetch(`${CHANNELS_API_BASE}/channels/bulk-update`, {
        method: 'PATCH',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ channel_ids: channelIds, ...updates })
      });

      if (response.ok) {
        await fetchChannels();
        await fetchChannelStats();
        channelsHook.setSelectedChannels(new Set());
        return true;
      } else {
        const errorData = await response.json();
        setError(errorData.detail || 'Failed to update channels');
        return false;
      }
    } catch (error) {
      console.error('Failed to update channels:', error);
      setError('Failed to update channels');
      return false;
    }
  };

  const updatePlatformChannels = async (platform: string, updates: { disabled?: boolean; internal?: boolean }) => {
    try {
      const response = await fetch(`${CHANNELS_API_BASE}/channels/platform/${platform}`, {
        method: 'PATCH',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(updates)
      });

      if (response.ok) {
        await fetchChannels();
        await fetchChannelStats();
        return true;
      } else {
        const errorData = await response.json();
        setError(errorData.detail || 'Failed to update platform channels');
        return false;
      }
    } catch (error) {
      console.error('Failed to update platform channels:', error);
      setError('Failed to update platform channels');
      return false;
    }
  };

  // Areas management functions
  const fetchAreas = async () => {
    channelsHook.setAreasLoading(true);
    try {
      const response = await fetch(`${CHANNELS_API_BASE}/areas`);
      if (response.ok) {
        const areasData = await response.json();
        channelsHook.setAreas(areasData.areas);
      } else {
        setError('Failed to fetch areas');
      }
    } catch (error) {
      console.error('Failed to fetch areas:', error);
      setError('Failed to fetch areas');
    } finally {
      channelsHook.setAreasLoading(false);
    }
  };

  const updateAreaChannels = async (areaName: string, updates: { disabled?: boolean; internal?: boolean }) => {
    try {
      const response = await fetch(`${CHANNELS_API_BASE}/channels/area/${encodeURIComponent(areaName)}`, {
        method: 'PATCH',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(updates)
      });

      if (response.ok) {
        await fetchChannels();
        await fetchChannelStats();
        return true;
      } else {
        const errorData = await response.json();
        setError(errorData.detail || 'Failed to update area channels');
        return false;
      }
    } catch (error) {
      console.error('Failed to update area channels:', error);
      setError('Failed to update area channels');
      return false;
    }
  };

  const updateCityChannels = async (cityName: string, updates: { disabled?: boolean; internal?: boolean }) => {
    try {
      const response = await fetch(`${CHANNELS_API_BASE}/channels/city/${encodeURIComponent(cityName)}`, {
        method: 'PATCH',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(updates)
      });

      if (response.ok) {
        await fetchChannels();
        await fetchChannelStats();
        return true;
      } else {
        const errorData = await response.json();
        setError(errorData.detail || 'Failed to update city channels');
        return false;
      }
    } catch (error) {
      console.error('Failed to update city channels:', error);
      setError('Failed to update city channels');
      return false;
    }
  };

  // InHouse channel management functions
  const fetchInhouseChannels = async () => {
    channelsHook.setInhouseLoading(true);
    try {
      const response = await fetch(`${CHANNELS_API_BASE}/inhouse`);
      if (response.ok) {
        const channelsData = await response.json();
        setInHouseChannels(channelsData);
      } else {
        setError('Failed to fetch InHouse channels');
      }
    } catch (error) {
      console.error('Failed to fetch InHouse channels:', error);
      setError('Failed to fetch InHouse channels');
    } finally {
      channelsHook.setInhouseLoading(false);
    }
  };

  const createInhouseChannel = async (channelData: InHouseChannelCreate) => {
    try {
      const response = await fetch(`${CHANNELS_API_BASE}/inhouse`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(channelData)
      });

      if (response.ok) {
        await fetchInhouseChannels();
        await fetchChannelStats();
        return true;
      } else {
        const errorData = await response.json();
        setError(errorData.detail || 'Failed to create InHouse channel');
        return false;
      }
    } catch (error) {
      console.error('Failed to create InHouse channel:', error);
      setError('Failed to create InHouse channel');
      return false;
    }
  };

  const updateInhouseChannel = async (channelId: number, updates: InHouseChannelUpdate) => {
    try {
      const response = await fetch(`${CHANNELS_API_BASE}/inhouse/${channelId}`, {
        method: 'PUT',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(updates)
      });

      if (response.ok) {
        await fetchInhouseChannels();
        await fetchChannelStats();
        return true;
      } else {
        const errorData = await response.json();
        setError(errorData.detail || 'Failed to update InHouse channel');
        return false;
      }
    } catch (error) {
      console.error('Failed to update InHouse channel:', error);
      setError('Failed to update InHouse channel');
      return false;
    }
  };

  const deleteInhouseChannel = async (channelId: number) => {
    try {
      const response = await fetch(`${CHANNELS_API_BASE}/inhouse/${channelId}`, {
        method: 'DELETE'
      });

      if (response.ok) {
        await fetchInhouseChannels();
        await fetchChannelStats();
        return true;
      } else {
        const errorData = await response.json();
        setError(errorData.detail || 'Failed to delete InHouse channel');
        return false;
      }
    } catch (error) {
      console.error('Failed to delete InHouse channel:', error);
      setError('Failed to delete InHouse channel');
      return false;
    }
  };


  const addToManagement = async (hostname: string) => {
    try {
      const device = discoveredDevices.find(d => d.hostname === hostname);
      if (!device) return;

      const deviceData: ManagedDeviceUpdateRequest = {
        device_name: device.friendly_name || hostname,
        api_key: 'uuPgF8JOAV/ZhFbDV4iS4Kwr1MV5H97p6Nk+HnpE0+g=',
        venue_name: '',
        location: '',
        notes: ''
      };

      const response = await fetch(`${API_BASE}/manage/${hostname}`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(deviceData)
      });

      if (!response.ok) {
        throw new Error('Failed to add device to management');
      }

      // Refresh data
      await devicesHook.fetchDevices();
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to add device');
    }
  };

  const forgetDevice = async (hostname: string) => {
    try {
      const response = await fetch(`${API_BASE}/discovered/${hostname}`, {
        method: 'DELETE'
      });

      if (!response.ok) {
        throw new Error('Failed to remove device from discovery');
      }

      // Refresh data
      await devicesHook.fetchDevices();
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to forget device');
    }
  };

  const removeFromManagement = async (deviceId: number) => {
    if (!confirm('Remove this IR sender?')) return;

    try {
      const response = await fetch(`${API_BASE}/managed/${deviceId}`, {
        method: 'DELETE'
      });

      if (!response.ok) {
        throw new Error('Failed to remove device');
      }

      await devicesHook.fetchDevices();
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to remove device');
    }
  };

  const syncDeviceStatus = async (deviceId: number) => {
    try {
      const response = await fetch(`${API_BASE}/managed/${deviceId}/health-check`, {
        method: 'POST'
      });
      if (!response.ok) {
        throw new Error('Health check request failed');
      }
      await devicesHook.fetchDevices();
    } catch (err) {
      console.error(err);
      setError('Failed to run device health check');
    }
  };

  const updateDevice = async (deviceId: number, deviceData: ManagedDeviceUpdateRequest) => {
    try {
      const response = await fetch(`${API_BASE}/managed/${deviceId}`, {
        method: 'PUT',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(deviceData)
      });

      if (!response.ok) {
        throw new Error('Failed to update device');
      }

      await devicesHook.fetchDevices();
      setEditingDevice(null);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to update device');
    }
  };

  const fetchDiscoveredDevices = useCallback(async () => {
    try {
      setLoading(true);
      setError(null);

      // Sync discovered devices first
      await fetch(`${API_BASE}/sync-discovered`, { method: 'POST' });

      // Fetch discovered devices
      const discoveredRes = await fetch(`${API_BASE}/discovered`);
      if (!discoveredRes.ok) {
        throw new Error('Failed to fetch discovered devices');
      }

      const discoveredData = await discoveredRes.json();
      setDiscoveredDevices(discoveredData);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to fetch discovered devices');
    } finally {
      setLoading(false);
    }
  }, [API_BASE]);

  useEffect(() => {
    fetchDiscoveredDevices();

    // Refresh every 30 seconds
    const interval = setInterval(() => {
      fetchDiscoveredDevices();
    }, 30000);
    return () => clearInterval(interval);
  }, [fetchDiscoveredDevices]);

  // Template summaries are handled by the templates hook

  useEffect(() => {
    if (currentPage === 'yaml-builder') {
      setCompileOutput(null);
      setBuilderError(null);
      fetchBuilderData(true);
      fetchBuilderData();
    } else if (currentPage === 'settings') {
      tagsHook.fetchTags(); // Refresh tags when visiting settings
      // Template summaries handled by hook
    }
  }, [currentPage, fetchBuilderData]);

  useEffect(() => {
    if (currentPage !== 'yaml-builder' || !builderInitialized || !templateId) {
      return;
    }
    requestPreview();
  }, [currentPage, builderInitialized, templateId, portAssignments, includeComments, requestPreview]);

  // Reset port configs when IR config modal opens/closes
  useEffect(() => {
    if (!showIRConfig) {
      setPortConfigs({});
      setConfigLocation('');
      setLocationMode('existing');
      return;
    }

    const initialLocation = showIRConfig.location || '';
    setConfigLocation(initialLocation);

    const availableLocations = Array.from(new Set(
      devicesHook.devices
        .map(device => device.location)
        .filter((location): location is string => Boolean(location))
    ));

    if (initialLocation && !availableLocations.includes(initialLocation)) {
      setLocationMode('custom');
    } else {
      setLocationMode('existing');
    }
  }, [showIRConfig, devicesHook.devices]);

  // Load channels data when channels tab is active
  useEffect(() => {
    if (currentPage === 'settings' && settingsTab === 'channels') {
      fetchChannels();
      fetchChannelStats();
      fetchAreas();
      fetchInhouseChannels();
    }
  }, [currentPage, settingsTab]);

  // Load InHouse channels when InHouse tab is active
  useEffect(() => {
    if (currentPage === 'settings' && settingsTab === 'channels' && channelTab === 'inhouse-channels') {
      fetchInhouseChannels();
    }
  }, [currentPage, settingsTab, channelTab]);

  // Reload channels when filters change
  useEffect(() => {
    if (currentPage === 'settings' && settingsTab === 'channels') {
      fetchChannels();
    }
  }, [channelFilters]);

  // Load channels when area is selected
  useEffect(() => {
    if (channelsHook.selectedAreaName && currentPage === 'settings' && settingsTab === 'channels') {
      fetchChannelsForArea(channelsHook.selectedAreaName);
    } else if (!channelsHook.selectedAreaName && currentPage === 'settings' && settingsTab === 'channels') {
      // Clear channels when no area is selected
      channelsHook.setChannels([]);
      channelsHook.setSelectedChannels(new Set());
    }
  }, [channelsHook.selectedAreaName, currentPage, settingsTab]);

  const unmanaged = discoveredDevices.filter(device => !device.is_managed);

  if (loading || devicesHook.loading) {
    return (
      <div className="container">
        <LoadingSpinner size="large" text="⚙️ Loading SmartVenue IR Control System..." />
      </div>
    );
  }

  // Sorting and filtering logic
  const sortedAndFilteredDevices = connectedDevices
    .filter(device => {
      return Object.entries(filters).every(([field, value]) => {
        if (!value) return true;
        if (field === 'tag') {
          return device.tags?.some(tag => tag.name.toLowerCase().includes(value.toLowerCase()));
        }
        return device[field as keyof ConnectedDevice]?.toString().toLowerCase().includes(value.toLowerCase());
      });
    })
    .sort((a, b) => {
      const aVal = a[sortField]?.toString() || '';
      const bVal = b[sortField]?.toString() || '';
      const comparison = aVal.localeCompare(bVal);
      return sortDirection === 'asc' ? comparison : -comparison;
    });

  // Bulk selection functions
  const handleDeviceSelection = (deviceId: string, isSelected: boolean) => {
    setSelectedDevices(prev => {
      const newSet = new Set(prev);
      if (isSelected) {
        newSet.add(deviceId);
      } else {
        newSet.delete(deviceId);
      }
      return newSet;
    });
  };

  const handleSelectAll = () => {
    setSelectedDevices(new Set(sortedAndFilteredDevices.map(d => d.id)));
  };

  const handleSelectNone = () => {
    setSelectedDevices(new Set());
  };

  const handleSelectByLocation = (location: string) => {
    const devicesInLocation = sortedAndFilteredDevices
      .filter(d => d.location === location)
      .map(d => d.id);

    // Check if all devices in this location are already selected
    const allSelected = devicesInLocation.every(id => selectedDevices.has(id));

    setSelectedDevices(prev => {
      const newSelected = new Set(prev);
      if (allSelected) {
        // Deselect all devices in this location
        devicesInLocation.forEach(id => newSelected.delete(id));
      } else {
        // Select all devices in this location
        devicesInLocation.forEach(id => newSelected.add(id));
      }
      return newSelected;
    });
  };

  const handleSelectByTag = (tagId: number) => {
    const devicesWithTag = sortedAndFilteredDevices
      .filter(d => d.tags?.some(tag => tag.id === tagId))
      .map(d => d.id);

    // Check if all devices with this tag are already selected
    const allSelected = devicesWithTag.every(id => selectedDevices.has(id));

    setSelectedDevices(prev => {
      const newSelected = new Set(prev);
      if (allSelected) {
        // Deselect all devices with this tag
        devicesWithTag.forEach(id => newSelected.delete(id));
      } else {
        // Select all devices with this tag
        devicesWithTag.forEach(id => newSelected.add(id));
      }
      return newSelected;
    });
  };

  const handleSort = (field: keyof ConnectedDevice) => {
    if (sortField === field) {
      setSortDirection(sortDirection === 'asc' ? 'desc' : 'asc');
    } else {
      setSortField(field);
      setSortDirection('asc');
    }
  };

  const handleFilter = (field: string, value: string) => {
    setFilters(prev => ({ ...prev, [field]: value }));
  };

  // Missing handler functions for Settings page components
  const handleSaveTemplate = async (e: React.FormEvent) => {
    e.preventDefault();
    // Template saving handled by templatesHook
  };

  const handleTagDelete = async (tagId: number) => {
    const success = await deleteDeviceTag(tagId);
    if (success) {
      await tagsHook.fetchTags(); // Refresh the tags list
    }
  };

  const handleSaveAreaChannels = async () => {
    if (!channelsHook.selectedAreaName) return;

    try {
      channelsHook.setChannelsSaving(true);

      // Get all area channels
      const allAreaChannels = channelsHook.channels.map(channel => channel.id);
      const selectedChannelIds = Array.from(channelsHook.selectedChannels);

      // Channels to enable (selected ones)
      if (selectedChannelIds.length > 0) {
        await bulkUpdateChannels(selectedChannelIds, { disabled: false, internal: false });
      }

      // Channels to disable (unselected ones in this area)
      const channelsToDisable = allAreaChannels.filter(id => !channelsHook.selectedChannels.has(id));
      if (channelsToDisable.length > 0) {
        await bulkUpdateChannels(channelsToDisable, { disabled: true });
      }

      // Refresh the area channels to show updated state
      await fetchChannelsForArea(channelsHook.selectedAreaName);
      await fetchChannelStats(); // Refresh stats
    } catch (error) {
      console.error('Failed to save area channels:', error);
      setError('Failed to save area channels');
    } finally {
      channelsHook.channelsHook.setChannelsSaving(false);
    }
  };

  const handleDeleteInHouseChannel = async (channelId: number) => {
    if (!confirm('Are you sure you want to delete this InHouse channel?')) return;

    const success = await deleteInhouseChannel(channelId);
    if (success) {
      await fetchInhouseChannels(); // Refresh the list
    }
  };

  const handleSaveInHouseChannel = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!channelsHook.editingInHouseChannel) return;

    try {
      let success = false;
      if ('id' in channelsHook.editingInHouseChannel && channelsHook.editingInHouseChannel.id) {
        // Update existing channel
        const channelId = channelsHook.editingInHouseChannel.id as number;
        const { id, ...updateData } = channelsHook.editingInHouseChannel;
        success = await updateInhouseChannel(channelId, updateData as InHouseChannelUpdate);
      } else {
        // Create new channel
        success = await createInhouseChannel(channelsHook.editingInHouseChannel as InHouseChannelCreate);
      }

      if (success) {
        channelsHook.setEditingInHouseChannel(null); // Close the modal/form
        await fetchInhouseChannels(); // Refresh the list
      }
    } catch (error) {
      console.error('Failed to save InHouse channel:', error);
      setError('Failed to save InHouse channel');
    }
  };

  return (
    <ErrorBoundary>
      <div className="container">
      {/* Header with Navigation */}
      <div className="header">
        <div>
          <h1>🏢 SmartVenue</h1>
          <p>IR Device Control System</p>
        </div>
        <div className="nav-tabs">
          <button
            className={`nav-tab ${currentPage === 'devices' ? 'active' : ''}`}
            onClick={() => setCurrentPage('devices')}
          >
            📺 Devices ({connectedDevices.length})
          </button>
          <button
            className={`nav-tab ${currentPage === 'ir-senders' ? 'active' : ''}`}
            onClick={() => setCurrentPage('ir-senders')}
          >
            📡 IR Senders ({devicesHook.devices.length})
          </button>
          <button
            className={`nav-tab ${currentPage === 'yaml-builder' ? 'active' : ''}`}
            onClick={() => setCurrentPage('yaml-builder')}
          >
            🧪 YAML Builder
          </button>
          <button
            className={`nav-tab ${currentPage === 'settings' ? 'active' : ''}`}
            onClick={() => setCurrentPage('settings')}
          >
            ⚙️ Settings
          </button>
        </div>
        <div className="header-actions">
          <button className="button secondary refresh-button" onClick={() => {
            fetchDiscoveredDevices();
            devicesHook.fetchDevices();
          }}>
            🔄 Refresh
          </button>
          <a
            href="http://100.93.158.19:8000/api/v1/admin/"
            target="_blank"
            rel="noopener noreferrer"
            className="button secondary"
            style={{ textDecoration: 'none', marginLeft: '8px' }}
          >
            🗄️ Database
          </a>
        </div>
      </div>

      {error && (
        <div className="error">
          ❌ {error}
        </div>
      )}

      {/* Page Content */}
      {currentPage === 'devices' && (
        <DevicesPage
          connectedDevices={connectedDevices}
          filters={filters}
          deviceTags={tagsHook.deviceTags}
          selectedDevices={selectedDevices}
          expandedDevice={expandedDevice}
          setCurrentPage={setCurrentPage}
          handleFilter={handleFilter}
          setSelectedDevices={setSelectedDevices}
          setExpandedDevice={setExpandedDevice}
        />
      )}

      {/* IR Senders Page */}
      {currentPage === 'ir-senders' && (
        <IRSendersPage
          discoveredDevices={discoveredDevices}
          managedDevices={devicesHook.devices}
          editingDevice={editingDevice}
          setEditingDevice={setEditingDevice}
          setShowIRConfig={setShowIRConfig}
          addToManagement={addToManagement}
          forgetDevice={forgetDevice}
          removeFromManagement={removeFromManagement}
          syncDeviceStatus={syncDeviceStatus}
        />
      )}

      {/* YAML Builder Page */}
      {currentPage === 'yaml-builder' && (
        <YamlBuilderPage
          builderError={builderError}
          builderLoading={builderLoading}
          templateCategories={templateCategories}
          selectedLibraries={selectedLibraries}
          portAssignments={portAssignments}
          yamlPreview={yamlPreview}
          yamlCharCount={yamlCharCount}
          baseTemplate={baseTemplate}
          includeComments={includeComments}
          previewLoading={previewLoading}
          compileOutput={compileOutput}
          compileLoading={compileLoading}
          downloadUrl={downloadUrl}
          binaryFilename={binaryFilename}
          setBuilderError={setBuilderError}
          setIncludeComments={setIncludeComments}
          handleSelectLibrary={handleSelectLibrary}
          handleRemoveLibrary={handleRemoveLibrary}
          handlePortAssignmentChange={handlePortAssignmentChange}
          handleSaveYaml={handleSaveYaml}
          handleSaveYamlToServer={handleSaveYamlToServer}
          handleCompile={handleCompile}
          compileOutputRef={compileOutputRef}
        />
      )}

      {/* Settings Page */}
      {currentPage === 'settings' && (
        <div style={{ padding: '20px', backgroundColor: '#f8f0ff' }}>
          <h2>⚙️ Settings</h2>
          <div style={{ padding: '20px', backgroundColor: '#fff3cd', border: '1px solid #ffeaa7', borderRadius: '5px', marginTop: '20px' }}>
            <p><strong>Settings functionality temporarily disabled</strong></p>
            <p>Tag Management has been removed to prevent application crashes. Other settings features will be restored soon.</p>
          </div>
        </div>
      )}

      {/* IR Configuration Modal */}
      {showIRConfig && (() => {
        const deviceLabel = showIRConfig.device_name || showIRConfig.hostname;
        const configuredPorts = showIRConfig.ir_ports
          ? showIRConfig.ir_ports.filter(port => Boolean(port.connected_device_name)).length
          : 0;
        const activePorts = showIRConfig.ir_ports
          ? showIRConfig.ir_ports.filter(port => port.is_active !== false).length
          : 0;

        const locationOptions = Array.from(new Set(
          devicesHook.devices
            .map(device => device.location)
            .filter((location): location is string => Boolean(location))
        ));

        return (
          <div className="modal-overlay" onClick={() => setShowIRConfig(null)}>
            <div className="modal large ir-config-modal" onClick={(e) => e.stopPropagation()}>
              <div className="modal-header">
                <div>
                  <span className="modal-eyebrow">IR control suite</span>
                  <h3>📺 Configure Devices</h3>
                  <p>Tailor each IR port and keep your venue devices organized.</p>
                </div>
                <div className="ir-config-header-meta">
                  <span className="ir-config-device-name">{deviceLabel}</span>
                  <span className="ir-config-device-host">{showIRConfig.hostname}</span>
                </div>
              </div>

              <div className="ir-config-summary">
                <div className="ir-config-summary-left">
                  <div className="ir-config-summary-label">Current IP</div>
                  <div className="ir-config-summary-value">{showIRConfig.current_ip_address}</div>
                </div>
                <div className="ir-config-summary-stats">
                  <div className="ir-config-stat">
                    <span className="ir-config-stat-value">{configuredPorts}/{showIRConfig.total_ir_ports}</span>
                    <span className="ir-config-stat-label">Configured Ports</span>
                  </div>
                  <div className="ir-config-stat">
                    <span className="ir-config-stat-value">{activePorts}</span>
                    <span className="ir-config-stat-label">Active Ports</span>
                  </div>
                </div>
                <div className="ir-config-location">
                  <label htmlFor="ir-config-location-select">📍 Location</label>
                  <div className="location-selector">
                    <select
                      id="ir-config-location-select"
                      value={locationMode === 'custom' ? '__custom__' : configLocation}
                      onChange={(e) => {
                        const value = e.target.value;
                        if (value === '__custom__') {
                          setLocationMode('custom');
                          setConfigLocation('');
                        } else {
                          setLocationMode('existing');
                          setConfigLocation(value);
                        }
                      }}
                    >
                      <option value="">Select location...</option>
                      {locationOptions.map(location => (
                        <option key={location} value={location}>
                          {location}
                        </option>
                      ))}
                      <option value="__custom__">+ Add new location</option>
                    </select>
                    {locationMode === 'custom' && (
                      <input
                        id="ir-config-location-input"
                        type="text"
                        value={configLocation}
                        onChange={(e) => setConfigLocation(e.target.value)}
                        placeholder="New location name"
                      />
                    )}
                  </div>
                </div>
              </div>

              <div className="modal-body">
                <div className="ir-config-grid">
                  {Array.from({ length: showIRConfig.total_ir_ports }, (_, i) => {
                    const port = showIRConfig.ir_ports?.find(p => p.port_number === i + 1);
                    return (
                      <IRPortConfig
                        key={i + 1}
                        portNumber={i + 1}
                        port={port}
                        onDataChange={handlePortDataChange}
                        availableTags={tagsHook.deviceTags}
                      />
                    );
                  })}
                </div>
              </div>

              <div className="modal-footer">
                <button className="button secondary" onClick={() => setShowIRConfig(null)}>
                  Cancel
                </button>
                <button className="button" onClick={saveIRConfiguration}>
                  Save Configuration
                </button>
              </div>
            </div>
          </div>
        );
      })()}
      </div>
    </ErrorBoundary>
  );
}

export default App;
