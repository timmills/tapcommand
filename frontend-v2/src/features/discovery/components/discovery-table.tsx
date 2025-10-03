import type { DiscoveredDevice } from '@/types';
import { formatDateTime, formatRelativeTime } from '@/utils/datetime';

interface DiscoveryTableProps {
  devices: DiscoveredDevice[];
  onSelect?: (device: DiscoveredDevice) => void;
}

const renderFriendlyName = (device: DiscoveredDevice) => device.friendly_name ?? device.hostname;

const renderCapabilities = (device: DiscoveredDevice) => {
  const capabilities = device.discovery_properties &&
    typeof device.discovery_properties === 'object' &&
    'capabilities' in device.discovery_properties
      ? (device.discovery_properties as Record<string, unknown>).capabilities
      : undefined;
  if (!capabilities || typeof capabilities !== 'object') {
    return '—';
  }
  const brandCandidates = (capabilities as Record<string, unknown>).brands;
  const commandCandidates = (capabilities as Record<string, unknown>).commands;
  const brands = Array.isArray(brandCandidates) ? (brandCandidates as unknown[]).map(String) : [];
  const commands = Array.isArray(commandCandidates) ? (commandCandidates as unknown[]).map(String) : [];
  const summaries: string[] = [];
  if (brands.length > 0) {
    summaries.push(`${brands.length} brands`);
  }
  if (commands.length > 0) {
    summaries.push(`${commands.length} commands`);
  }
  return summaries.join(' • ') || '—';
};

export const DiscoveryTable = ({ devices, onSelect }: DiscoveryTableProps) => {
  if (devices.length === 0) {
    return (
      <div className="rounded-md border border-dashed border-slate-300 bg-white p-8 text-center text-sm text-slate-500">
        Discovery service has not found any ESPHome IR controllers yet. Start scanning to populate this list.
      </div>
    );
  }

  return (
    <div className="overflow-hidden rounded-lg border border-slate-200 bg-white shadow-sm">
      <table className="min-w-full divide-y divide-slate-200">
        <thead className="bg-slate-50">
          <tr>
            <th className="px-4 py-3 text-left text-xs font-semibold uppercase tracking-wide text-slate-500">Device</th>
            <th className="px-4 py-3 text-left text-xs font-semibold uppercase tracking-wide text-slate-500">Network</th>
            <th className="px-4 py-3 text-left text-xs font-semibold uppercase tracking-wide text-slate-500">Capabilities</th>
            <th className="px-4 py-3 text-left text-xs font-semibold uppercase tracking-wide text-slate-500">Last Seen</th>
          </tr>
        </thead>
        <tbody className="divide-y divide-slate-100">
          {devices.map((device) => (
            <tr
              key={device.id ?? device.hostname}
              className={`hover:bg-slate-50/70 ${onSelect ? 'cursor-pointer' : ''}`}
              onClick={() => onSelect?.(device)}
            >
              <td className="px-4 py-3 align-top">
                <div className="text-sm font-medium text-slate-900">{renderFriendlyName(device)}</div>
                <div className="text-xs text-slate-500">{device.hostname}</div>
              </td>
              <td className="px-4 py-3 align-top text-sm text-slate-600">
                <div>{device.ip_address}</div>
                <div className="text-xs text-slate-500 uppercase">{device.mac_address}</div>
              </td>
              <td className="px-4 py-3 align-top text-sm text-slate-600">{renderCapabilities(device)}</td>
              <td className="px-4 py-3 align-top text-sm text-slate-600" title={formatDateTime(device.last_seen)}>
                {formatRelativeTime(device.last_seen)}
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
};
