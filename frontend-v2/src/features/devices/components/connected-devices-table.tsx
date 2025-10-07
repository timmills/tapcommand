import { useState, useMemo } from 'react';
import type { DeviceTag, ManagedDevice } from '@/types';
import { formatRelativeTime } from '@/utils/datetime';
import { usePortStatus, getPowerStateForPort } from '../hooks/use-port-status';
import { useVirtualDevices } from '../hooks/use-virtual-devices';

interface ConnectedDevice {
  id: string;
  deviceName: string;
  controllerName: string;
  controllerHostname: string;
  controllerLocation: string;
  portNumber: number;
  tags: DeviceTag[];
  status: 'online' | 'offline';
  updatedAt: string;
  controller: ManagedDevice;
}

interface ConnectedDevicesTableProps {
  controllers: ManagedDevice[];
  tags?: DeviceTag[];
  onEditController?: (controller: ManagedDevice) => void;
}

type SortField = 'device' | 'controller' | 'location' | 'lastSeen';
type SortDirection = 'asc' | 'desc';

const buildConnectedDevices = (controllers: ManagedDevice[], tagMap: Map<number, DeviceTag>): ConnectedDevice[] => {
  return controllers.flatMap((controller) => {
    return controller.ir_ports
      .filter((port) => port.is_active)
      .map((port) => ({
        id: `${controller.id}-${port.id ?? port.port_number}`,
        deviceName: port.connected_device_name || `Port ${port.port_number}`,
        controllerName: controller.device_name ?? controller.hostname,
        controllerHostname: controller.hostname,
        controllerLocation: controller.location ?? '—',
        portNumber: port.port_number,
        tags: (port.tag_ids ?? [])
          .map((tagId) => tagMap.get(tagId))
          .filter((tag): tag is DeviceTag => Boolean(tag)),
        status: controller.is_online ? 'online' : 'offline',
        updatedAt: controller.last_seen,
        controller,
      }));
  });
};

export const ConnectedDevicesTable = ({ controllers, tags = [], onEditController }: ConnectedDevicesTableProps) => {
  const [sortField, setSortField] = useState<SortField>('device');
  const [sortDirection, setSortDirection] = useState<SortDirection>('asc');
  const { data: virtualDevices = [] } = useVirtualDevices();

  const tagMap = new Map(tags.map((tag) => [tag.id, tag] as const));
  const connectedDevices = buildConnectedDevices(controllers, tagMap);

  const sortedDevices = useMemo(() => {
    const sorted = [...connectedDevices];
    sorted.sort((a, b) => {
      let comparison = 0;

      switch (sortField) {
        case 'device':
          comparison = a.deviceName.localeCompare(b.deviceName);
          break;
        case 'controller':
          comparison = a.controllerName.localeCompare(b.controllerName);
          break;
        case 'location':
          comparison = a.controllerLocation.localeCompare(b.controllerLocation);
          break;
        case 'lastSeen':
          comparison = new Date(a.updatedAt).getTime() - new Date(b.updatedAt).getTime();
          break;
      }

      return sortDirection === 'asc' ? comparison : -comparison;
    });
    return sorted;
  }, [connectedDevices, sortField, sortDirection]);

  const handleSort = (field: SortField) => {
    if (sortField === field) {
      setSortDirection(sortDirection === 'asc' ? 'desc' : 'asc');
    } else {
      setSortField(field);
      setSortDirection('asc');
    }
  };

  if (connectedDevices.length === 0) {
    return (
      <div className="rounded-md border border-dashed border-slate-300 bg-white p-8 text-center text-sm text-slate-500">
        No connected devices reported yet. Assign IR libraries to controller ports to see devices here.
      </div>
    );
  }

  const SortableHeader = ({ field, children }: { field: SortField; children: React.ReactNode }) => {
    const isActive = sortField === field;
    return (
      <th className="px-4 py-3 text-left">
        <button
          type="button"
          onClick={() => handleSort(field)}
          className="group flex items-center gap-1.5 text-xs font-semibold uppercase tracking-wide text-slate-500 transition hover:text-slate-700"
        >
          {children}
          <span className={`transition ${isActive ? 'opacity-100' : 'opacity-0 group-hover:opacity-50'}`}>
            {isActive && sortDirection === 'asc' ? (
              <svg className="h-3.5 w-3.5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 15l7-7 7 7" />
              </svg>
            ) : (
              <svg className="h-3.5 w-3.5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 9l-7 7-7-7" />
              </svg>
            )}
          </span>
        </button>
      </th>
    );
  };

  return (
    <div className="overflow-hidden rounded-lg border border-slate-200 bg-white shadow-sm">
      <table className="min-w-full divide-y divide-slate-200">
        <thead className="bg-slate-50">
          <tr>
            <SortableHeader field="device">Device</SortableHeader>
            <SortableHeader field="controller">Controller</SortableHeader>
            <SortableHeader field="location">Location</SortableHeader>
            <SortableHeader field="lastSeen">Last seen</SortableHeader>
            <th className="px-4 py-3 text-left text-xs font-semibold uppercase tracking-wide text-slate-500">Power</th>
            <th className="px-4 py-3 text-left text-xs font-semibold uppercase tracking-wide text-slate-500">Tags</th>
            {onEditController ? (
              <th className="px-4 py-3 text-right text-xs font-semibold uppercase tracking-wide text-slate-500">Actions</th>
            ) : null}
          </tr>
        </thead>
        <tbody className="divide-y divide-slate-100">
          {sortedDevices.map((device) => {
            // Find linked network TV for this IR port
            const linkedDevice = virtualDevices.find(
              vd => vd.fallback_ir_controller === device.controllerHostname && vd.fallback_ir_port === device.portNumber
            );

            return (
              <tr key={device.id} className="hover:bg-slate-50/70">
                <td className="px-4 py-3 align-top">
                  <div className="space-y-1">
                    <div className="text-sm font-medium text-slate-900">{device.deviceName}</div>
                    {linkedDevice && (
                      <div className="flex items-center gap-1.5 text-xs text-blue-600">
                        <svg className="h-3.5 w-3.5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M13 10V3L4 14h7v7l9-11h-7z" />
                        </svg>
                        <span className="font-medium">{linkedDevice.device_name}</span>
                        <span className="text-slate-500">({linkedDevice.ip_address})</span>
                      </div>
                    )}
                  </div>
                </td>
              <td className="px-4 py-3 align-top text-sm text-slate-600">
                <div>{device.controllerName}</div>
                <div className="text-xs text-slate-500">{device.controllerHostname}</div>
              </td>
              <td className="px-4 py-3 align-top text-sm text-slate-600">{device.controllerLocation}</td>
              <td className="px-4 py-3 align-top text-sm text-slate-600">{formatRelativeTime(device.updatedAt)}</td>
              <td className="px-4 py-3 align-top">
                <PowerIndicator hostname={device.controllerHostname} port={device.portNumber} />
              </td>
              <td className="px-4 py-3 align-top">
                <div className="flex flex-wrap gap-2">
                  {device.tags.length ? (
                    device.tags.map((tag) => (
                      <span
                        key={tag.id}
                        className="inline-flex items-center rounded-full border px-2 py-1 text-xs font-medium text-slate-700 shadow-sm"
                        style={{ borderColor: tag.color ?? '#cbd5f5' }}
                      >
                        {tag.name}
                      </span>
                    ))
                  ) : (
                    <span className="text-sm text-slate-400">—</span>
                  )}
                </div>
              </td>
              {onEditController ? (
                <td className="px-4 py-3 align-top text-right">
                  <button
                    type="button"
                    onClick={() => onEditController(device.controller)}
                    className="inline-flex items-center rounded-md border border-slate-200 bg-white px-3 py-1.5 text-xs font-medium text-slate-700 shadow-sm transition hover:bg-slate-50"
                  >
                    Edit
                  </button>
                </td>
              ) : null}
            </tr>
            );
          })}
        </tbody>
      </table>
    </div>
  );
};

const PowerIndicator = ({ hostname, port }: { hostname: string; port: number }) => {
  const { data: portStatus } = usePortStatus(hostname);
  const powerState = getPowerStateForPort(portStatus, port);

  if (!powerState) {
    return <span className="text-xs text-slate-400">—</span>;
  }

  return (
    <div className="flex items-center gap-2">
      <div
        className={`h-2.5 w-2.5 rounded-full ${
          powerState === 'on' ? 'bg-green-500' : 'bg-red-500'
        }`}
      />
      <span className="text-xs text-slate-600 capitalize">{powerState}</span>
    </div>
  );
};
