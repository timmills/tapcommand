import { useState } from 'react';
import type { ManagedDevice } from '@/types';
import { formatDateTime, formatRelativeTime } from '@/utils/datetime';
import { sendDiagnosticSignal } from '../api/devices-api';

interface ControllerTableProps {
  controllers: ManagedDevice[];
  onEdit?: (controller: ManagedDevice) => void;
}

export const ControllerTable = ({ controllers, onEdit }: ControllerTableProps) => {
  const devices = controllers;
  const [identifyingDevices, setIdentifyingDevices] = useState<Set<number>>(new Set());

  const handleIdentify = async (controller: ManagedDevice) => {
    if (identifyingDevices.has(controller.id)) return;

    setIdentifyingDevices(prev => new Set(prev).add(controller.id));

    try {
      await sendDiagnosticSignal(controller.hostname, 0, 1);
      // Note: In a real implementation, you'd want to show a success notification
    } catch (error) {
      console.error('Failed to send diagnostic signal:', error);
      // Note: In a real implementation, you'd want to show an error notification
    } finally {
      setIdentifyingDevices(prev => {
        const newSet = new Set(prev);
        newSet.delete(controller.id);
        return newSet;
      });
    }
  };
  if (devices.length === 0) {
    return (
      <div className="rounded-md border border-dashed border-slate-300 bg-white p-8 text-center text-sm text-slate-500">
        No IR controllers registered yet. Once you adopt a controller it will appear here.
      </div>
    );
  }

  return (
    <div className="overflow-hidden rounded-lg border border-slate-200 bg-white shadow-sm">
      <table className="min-w-full divide-y divide-slate-200">
        <thead className="bg-slate-50">
          <tr>
            <th className="px-4 py-3 text-left text-xs font-semibold uppercase tracking-wide text-slate-500">Hostname</th>
            <th className="px-4 py-3 text-left text-xs font-semibold uppercase tracking-wide text-slate-500">Location</th>
            <th className="px-4 py-3 text-left text-xs font-semibold uppercase tracking-wide text-slate-500">IP / MAC</th>
            <th className="px-4 py-3 text-left text-xs font-semibold uppercase tracking-wide text-slate-500">IR Ports</th>
            <th className="px-4 py-3 text-left text-xs font-semibold uppercase tracking-wide text-slate-500">Status</th>
            <th className="px-4 py-3 text-left text-xs font-semibold uppercase tracking-wide text-slate-500">Last Seen</th>
            {onEdit ? (
              <th className="px-4 py-3 text-right text-xs font-semibold uppercase tracking-wide text-slate-500">Actions</th>
            ) : null}
          </tr>
        </thead>
        <tbody className="divide-y divide-slate-100">
          {devices.map((controller) => {
            const activePorts = controller.ir_ports.filter((port) => port.is_active).length;
            const totalPorts = controller.ir_ports.length || controller.total_ir_ports;
            return (
              <tr key={controller.id} className="hover:bg-slate-50/70">
                <td className="px-4 py-3 align-top">
                  <div className="text-sm font-medium text-slate-900">{controller.device_name ?? controller.hostname}</div>
                  <div className="text-xs text-slate-500">{controller.hostname}</div>
                </td>
                <td className="px-4 py-3 align-top">
                  <div className="text-sm text-slate-700">{controller.location ?? '—'}</div>
                  <div className="text-xs text-slate-500">{controller.venue_name ?? 'Unassigned venue'}</div>
                </td>
                <td className="px-4 py-3 align-top text-sm text-slate-600">
                  <div>{controller.current_ip_address}</div>
                  <div className="text-xs text-slate-500 uppercase">{controller.mac_address}</div>
                </td>
                <td className="px-4 py-3 align-top text-sm text-slate-600">
                  {activePorts}/{totalPorts} active
                </td>
                <td className="px-4 py-3 align-top">
                  <span
                    className={`inline-flex items-center rounded-full px-2.5 py-1 text-xs font-semibold ${
                      controller.is_online
                        ? 'bg-green-50 text-green-700 ring-1 ring-inset ring-green-600/20'
                        : 'bg-rose-50 text-rose-700 ring-1 ring-inset ring-rose-600/20'
                    }`}
                  >
                    {controller.is_online ? 'Online' : 'Offline'}
                  </span>
                </td>
                <td className="px-4 py-3 align-top text-sm text-slate-600" title={formatDateTime(controller.last_seen)}>
                  {formatRelativeTime(controller.last_seen)}
                </td>
                {onEdit ? (
                  <td className="px-4 py-3 align-top text-right">
                    <div className="flex items-center gap-2">
                      <button
                        type="button"
                        onClick={() => handleIdentify(controller)}
                        disabled={identifyingDevices.has(controller.id)}
                        className={`inline-flex items-center rounded-md border px-3 py-1.5 text-xs font-medium shadow-sm transition ${
                          identifyingDevices.has(controller.id)
                            ? 'border-orange-200 bg-orange-50 text-orange-600 cursor-not-allowed'
                            : 'border-orange-200 bg-white text-orange-700 hover:bg-orange-50'
                        }`}
                        title="Flash device LED for identification"
                      >
                        {identifyingDevices.has(controller.id) ? 'Identifying...' : 'ID'}
                      </button>
                      <button
                        type="button"
                        onClick={() => onEdit(controller)}
                        className="inline-flex items-center rounded-md border border-slate-200 bg-white px-3 py-1.5 text-xs font-medium text-slate-700 shadow-sm transition hover:bg-slate-50"
                      >
                        Edit
                      </button>
                    </div>
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
