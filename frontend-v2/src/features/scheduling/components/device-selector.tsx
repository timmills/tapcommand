import { useState, useMemo } from 'react';
import { useManagedDevices } from '@/features/devices/hooks/use-managed-devices';
import { useDeviceTags } from '@/features/settings/hooks/use-device-tags';
import type { IRPort, DeviceTag } from '@/types';

interface DeviceSelectorProps {
  targetType: string;
  targetData: Record<string, any>;
  onChange: (targetType: string, targetData: Record<string, any>) => void;
}

export function DeviceSelector({ targetType, targetData, onChange }: DeviceSelectorProps) {
  const { data: managedDevices } = useManagedDevices();
  const { data: tags } = useDeviceTags();
  const [searchTerm, setSearchTerm] = useState('');

  // Build list of all IR ports
  const allPorts = useMemo(() => {
    if (!managedDevices) return [];

    const ports: Array<IRPort & { controllerName: string; location: string }> = [];
    for (const device of managedDevices) {
      for (const port of device.ir_ports || []) {
        if (port.is_active) {
          ports.push({
            ...port,
            controllerName: device.device_name || device.hostname,
            location: device.location || 'Unknown',
          });
        }
      }
    }
    return ports;
  }, [managedDevices]);

  // Filter ports by search
  const filteredPorts = useMemo(() => {
    if (!searchTerm) return allPorts;
    const term = searchTerm.toLowerCase();
    return allPorts.filter(
      (port) =>
        port.connected_device_name?.toLowerCase().includes(term) ||
        port.controllerName.toLowerCase().includes(term) ||
        port.location.toLowerCase().includes(term)
    );
  }, [allPorts, searchTerm]);

  // Get selected device IDs
  const selectedDeviceIds = (targetData.device_ids || []) as number[];
  const selectedTagIds = (targetData.tag_ids || []) as number[];
  const selectedLocations = (targetData.locations || []) as string[];

  // Handle selection changes
  const handleTargetTypeChange = (newType: string) => {
    if (newType === 'all') {
      onChange('all', {});
    } else if (newType === 'selection') {
      onChange('selection', { device_ids: [] });
    } else if (newType === 'tag') {
      onChange('tag', { tag_ids: [] });
    } else if (newType === 'location') {
      onChange('location', { locations: [] });
    }
  };

  const toggleDevice = (deviceId: number) => {
    const newIds = selectedDeviceIds.includes(deviceId)
      ? selectedDeviceIds.filter((id) => id !== deviceId)
      : [...selectedDeviceIds, deviceId];
    onChange('selection', { device_ids: newIds });
  };

  const toggleTag = (tagId: number) => {
    const newIds = selectedTagIds.includes(tagId)
      ? selectedTagIds.filter((id) => id !== tagId)
      : [...selectedTagIds, tagId];
    onChange('tag', { tag_ids: newIds });
  };

  const toggleLocation = (location: string) => {
    const newLocs = selectedLocations.includes(location)
      ? selectedLocations.filter((loc) => loc !== location)
      : [...selectedLocations, location];
    onChange('location', { locations: newLocs });
  };

  // Get unique locations
  const uniqueLocations = useMemo(() => {
    const locs = new Set<string>();
    allPorts.forEach((port) => {
      if (port.location) locs.add(port.location);
    });
    return Array.from(locs).sort();
  }, [allPorts]);

  // Count selected devices
  const selectedCount = useMemo(() => {
    if (targetType === 'all') return allPorts.length;
    if (targetType === 'selection') return selectedDeviceIds.length;
    if (targetType === 'tag') {
      return allPorts.filter((port) =>
        selectedTagIds.some((tagId) => port.tag_ids?.includes(tagId))
      ).length;
    }
    if (targetType === 'location') {
      return allPorts.filter((port) => selectedLocations.includes(port.location)).length;
    }
    return 0;
  }, [targetType, allPorts, selectedDeviceIds, selectedTagIds, selectedLocations]);

  return (
    <div className="space-y-4">
      {/* Target Type Selection */}
      <div>
        <label className="block text-sm font-medium text-slate-700 mb-2">Target Type</label>
        <div className="grid grid-cols-4 gap-2">
          <button
            type="button"
            onClick={() => handleTargetTypeChange('all')}
            className={`px-3 py-2 text-sm font-medium rounded-md ${
              targetType === 'all'
                ? 'bg-brand-600 text-white'
                : 'bg-white border border-slate-300 text-slate-700 hover:bg-slate-50'
            }`}
          >
            All Devices
          </button>
          <button
            type="button"
            onClick={() => handleTargetTypeChange('selection')}
            className={`px-3 py-2 text-sm font-medium rounded-md ${
              targetType === 'selection'
                ? 'bg-brand-600 text-white'
                : 'bg-white border border-slate-300 text-slate-700 hover:bg-slate-50'
            }`}
          >
            Selection
          </button>
          <button
            type="button"
            onClick={() => handleTargetTypeChange('tag')}
            className={`px-3 py-2 text-sm font-medium rounded-md ${
              targetType === 'tag'
                ? 'bg-brand-600 text-white'
                : 'bg-white border border-slate-300 text-slate-700 hover:bg-slate-50'
            }`}
          >
            By Tag
          </button>
          <button
            type="button"
            onClick={() => handleTargetTypeChange('location')}
            className={`px-3 py-2 text-sm font-medium rounded-md ${
              targetType === 'location'
                ? 'bg-brand-600 text-white'
                : 'bg-white border border-slate-300 text-slate-700 hover:bg-slate-50'
            }`}
          >
            By Location
          </button>
        </div>
      </div>

      {/* Selection Count */}
      <div className="text-sm text-slate-600">
        Selected: <span className="font-semibold">{selectedCount}</span> devices
      </div>

      {/* Device Selection */}
      {targetType === 'selection' && (
        <div>
          <div className="flex items-center justify-between mb-2">
            <label className="text-sm font-medium text-slate-700">Select Devices</label>
            <input
              type="text"
              placeholder="Search..."
              value={searchTerm}
              onChange={(e) => setSearchTerm(e.target.value)}
              className="text-sm rounded-md border-slate-300 shadow-sm focus:border-brand-500 focus:ring-brand-500"
            />
          </div>
          <div className="max-h-64 overflow-y-auto border border-slate-200 rounded-md">
            {filteredPorts.map((port) => (
              <label
                key={port.id}
                className="flex items-center gap-3 p-3 hover:bg-slate-50 cursor-pointer border-b border-slate-100 last:border-b-0"
              >
                <input
                  type="checkbox"
                  checked={selectedDeviceIds.includes(port.id)}
                  onChange={() => toggleDevice(port.id)}
                  className="h-4 w-4 rounded border-slate-300 text-brand-600 focus:ring-brand-500"
                />
                <div className="flex-1">
                  <div className="text-sm font-medium text-slate-900">
                    {port.connected_device_name || `Port ${port.port_number}`}
                  </div>
                  <div className="text-xs text-slate-500">
                    {port.controllerName} • {port.location}
                  </div>
                </div>
              </label>
            ))}
          </div>
        </div>
      )}

      {/* Tag Selection */}
      {targetType === 'tag' && (
        <div>
          <label className="block text-sm font-medium text-slate-700 mb-2">Select Tags</label>
          <div className="space-y-2">
            {tags?.map((tag: DeviceTag) => (
              <label
                key={tag.id}
                className="flex items-center gap-3 p-3 border border-slate-200 rounded-md hover:bg-slate-50 cursor-pointer"
              >
                <input
                  type="checkbox"
                  checked={selectedTagIds.includes(tag.id)}
                  onChange={() => toggleTag(tag.id)}
                  className="h-4 w-4 rounded border-slate-300 text-brand-600 focus:ring-brand-500"
                />
                <div
                  className="w-3 h-3 rounded-full"
                  style={{ backgroundColor: tag.color || '#cbd5e1' }}
                />
                <div className="flex-1">
                  <div className="text-sm font-medium text-slate-900">{tag.name}</div>
                  {tag.description && (
                    <div className="text-xs text-slate-500">{tag.description}</div>
                  )}
                </div>
                <div className="text-xs text-slate-500">{tag.usage_count} devices</div>
              </label>
            ))}
          </div>
        </div>
      )}

      {/* Location Selection */}
      {targetType === 'location' && (
        <div>
          <label className="block text-sm font-medium text-slate-700 mb-2">Select Locations</label>
          <div className="space-y-2">
            {uniqueLocations.map((location) => {
              const count = allPorts.filter((p) => p.location === location).length;
              return (
                <label
                  key={location}
                  className="flex items-center gap-3 p-3 border border-slate-200 rounded-md hover:bg-slate-50 cursor-pointer"
                >
                  <input
                    type="checkbox"
                    checked={selectedLocations.includes(location)}
                    onChange={() => toggleLocation(location)}
                    className="h-4 w-4 rounded border-slate-300 text-brand-600 focus:ring-brand-500"
                  />
                  <div className="flex-1">
                    <div className="text-sm font-medium text-slate-900">{location}</div>
                  </div>
                  <div className="text-xs text-slate-500">{count} devices</div>
                </label>
              );
            })}
          </div>
        </div>
      )}
    </div>
  );
}
