import { useState, useEffect } from 'react';
import { apiClient } from '@/lib/axios';
import { useManagedDevices } from '../hooks/use-managed-devices';
import type { ManagedDevice } from '@/types';

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

interface VirtualDeviceIRFallbackModalProps {
  device: VirtualDevice | null;
  open: boolean;
  onClose: () => void;
  onSaved?: () => void;
}

export const VirtualDeviceIRFallbackModal = ({
  device,
  open,
  onClose,
  onSaved,
}: VirtualDeviceIRFallbackModalProps) => {
  const { data: managedDevices } = useManagedDevices();
  const [isEditing, setIsEditing] = useState(false);
  const [saving, setSaving] = useState(false);
  const [selectedController, setSelectedController] = useState<string>('');
  const [selectedPort, setSelectedPort] = useState<number>(1);
  const [powerOnMethod, setPowerOnMethod] = useState<string>('hybrid');
  const [controlStrategy, setControlStrategy] = useState<string>('hybrid_ir_fallback');

  // Get IR controllers only
  const irControllers = (managedDevices ?? []).filter(
    (d) => d.device_type === 'ir_controller' || d.device_type === 'universal'
  );

  // Get available ports for selected controller
  const availablePorts = irControllers
    .find((c) => c.hostname === selectedController)
    ?.ir_ports.filter((p) => p.is_active) ?? [];

  useEffect(() => {
    if (!open || !device) return;

    setIsEditing(false);

    if (device.fallback_ir_controller && device.fallback_ir_port) {
      setSelectedController(device.fallback_ir_controller);
      setSelectedPort(device.fallback_ir_port);
    } else if (irControllers.length > 0) {
      setSelectedController(irControllers[0].hostname);
      setSelectedPort(1);
    }

    setPowerOnMethod(device.power_on_method || 'hybrid');
    setControlStrategy(device.control_strategy || 'hybrid_ir_fallback');
  }, [open, device, irControllers.length]);

  if (!open || !device) return null;

  const hasIRFallback = Boolean(device.fallback_ir_controller && device.fallback_ir_port);

  const handleSave = async () => {
    setSaving(true);
    try {
      await apiClient.post(`/api/v1/hybrid-devices/${device.id}/link-ir-fallback`, {
        ir_controller_hostname: selectedController,
        ir_port: selectedPort,
        power_on_method: powerOnMethod,
        control_strategy: controlStrategy,
      });

      setIsEditing(false);
      onSaved?.();
    } catch (error) {
      console.error('Failed to save IR fallback:', error);
      alert('Failed to save IR fallback configuration');
    } finally {
      setSaving(false);
    }
  };

  const handleUnlink = async () => {
    if (!confirm('Are you sure you want to remove the IR fallback for this device?')) {
      return;
    }

    setSaving(true);
    try {
      await apiClient.delete(`/api/v1/hybrid-devices/${device.id}/unlink-ir-fallback`);

      setIsEditing(false);
      onSaved?.();
    } catch (error) {
      console.error('Failed to unlink IR fallback:', error);
      alert('Failed to remove IR fallback configuration');
    } finally {
      setSaving(false);
    }
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/50">
      <div className="mx-4 w-full max-w-lg rounded-lg bg-white p-6 shadow-xl">
        <h3 className="text-lg font-semibold text-slate-900">IR Fallback Configuration</h3>

        <div className="mt-4 space-y-4">
          {/* Device Info */}
          <div className="rounded-lg border border-slate-200 bg-slate-50 p-3">
            <div className="flex items-center gap-3">
              <div className="flex h-10 w-10 items-center justify-center rounded-lg bg-brand-100">
                <svg className="h-6 w-6 text-brand-600" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9.75 17L9 20l-1 1h8l-1-1-.75-3M3 13h18M5 17h14a2 2 0 002-2V5a2 2 0 00-2-2H5a2 2 0 00-2 2v10a2 2 0 002 2z" />
                </svg>
              </div>
              <div className="flex-1">
                <h4 className="font-medium text-slate-900">{device.device_name}</h4>
                <p className="text-sm text-slate-500">{device.ip_address} • {device.protocol || 'Network'}</p>
              </div>
            </div>
          </div>

          {/* Current Configuration or Edit Form */}
          {!isEditing && hasIRFallback ? (
            <div className="rounded-lg border border-green-200 bg-green-50 p-4">
              <div className="flex items-start justify-between">
                <div>
                  <h4 className="text-sm font-medium text-green-900">IR Fallback Configured</h4>
                  <div className="mt-2 space-y-1 text-sm text-green-700">
                    <div>Controller: <span className="font-medium">{device.fallback_ir_controller}</span></div>
                    <div>Port: <span className="font-medium">{device.fallback_ir_port}</span></div>
                    <div>Power Method: <span className="font-medium">{device.power_on_method}</span></div>
                    <div>Strategy: <span className="font-medium">{device.control_strategy}</span></div>
                  </div>
                </div>
                <button
                  onClick={() => setIsEditing(true)}
                  className="rounded-md border border-green-300 bg-white px-3 py-1.5 text-xs font-medium text-green-700 shadow-sm transition hover:bg-green-50"
                >
                  Edit
                </button>
              </div>
            </div>
          ) : (
            <div className="space-y-4">
              {/* IR Controller Selection */}
              <div>
                <label className="block text-sm font-medium text-slate-700">IR Controller</label>
                <select
                  value={selectedController}
                  onChange={(e) => {
                    setSelectedController(e.target.value);
                    setSelectedPort(1); // Reset to port 1 when controller changes
                  }}
                  className="mt-1 block w-full rounded-md border border-slate-300 px-3 py-2 text-sm shadow-sm focus:border-brand-500 focus:outline-none focus:ring-1 focus:ring-brand-500"
                  disabled={saving}
                >
                  {irControllers.map((controller) => (
                    <option key={controller.hostname} value={controller.hostname}>
                      {controller.device_name || controller.hostname} ({controller.current_ip_address})
                    </option>
                  ))}
                </select>
              </div>

              {/* Port Selection */}
              <div>
                <label className="block text-sm font-medium text-slate-700">IR Port</label>
                <select
                  value={selectedPort}
                  onChange={(e) => setSelectedPort(parseInt(e.target.value))}
                  className="mt-1 block w-full rounded-md border border-slate-300 px-3 py-2 text-sm shadow-sm focus:border-brand-500 focus:outline-none focus:ring-1 focus:ring-brand-500"
                  disabled={saving}
                >
                  {availablePorts.map((port) => (
                    <option key={port.port_number} value={port.port_number}>
                      Port {port.port_number} {port.connected_device_name ? `- ${port.connected_device_name}` : ''}
                    </option>
                  ))}
                </select>
                {availablePorts.length === 0 && (
                  <p className="mt-1 text-xs text-red-600">No active ports on selected controller</p>
                )}
              </div>

              {/* Power On Method */}
              <div>
                <label className="block text-sm font-medium text-slate-700">Power On Method</label>
                <select
                  value={powerOnMethod}
                  onChange={(e) => setPowerOnMethod(e.target.value)}
                  className="mt-1 block w-full rounded-md border border-slate-300 px-3 py-2 text-sm shadow-sm focus:border-brand-500 focus:outline-none focus:ring-1 focus:ring-brand-500"
                  disabled={saving}
                >
                  <option value="ir">IR Only</option>
                  <option value="network">Network Only</option>
                  <option value="hybrid">Hybrid (Network first, IR fallback)</option>
                </select>
                <p className="mt-1 text-xs text-slate-500">
                  Recommended: Hybrid for Samsung legacy TVs
                </p>
              </div>

              {/* Control Strategy */}
              <div>
                <label className="block text-sm font-medium text-slate-700">Control Strategy</label>
                <select
                  value={controlStrategy}
                  onChange={(e) => setControlStrategy(e.target.value)}
                  className="mt-1 block w-full rounded-md border border-slate-300 px-3 py-2 text-sm shadow-sm focus:border-brand-500 focus:outline-none focus:ring-1 focus:ring-brand-500"
                  disabled={saving}
                >
                  <option value="network_only">Network Only</option>
                  <option value="ir_only">IR Only</option>
                  <option value="hybrid_ir_fallback">Hybrid (Network with IR Fallback)</option>
                </select>
                <p className="mt-1 text-xs text-slate-500">
                  Controls all commands, not just power
                </p>
              </div>

              {/* Info Box */}
              <div className="rounded-lg border border-blue-200 bg-blue-50 p-3">
                <h4 className="text-sm font-medium text-blue-900">How it works</h4>
                <ul className="mt-2 space-y-1 text-xs text-blue-700">
                  <li>✓ Network commands are fast and provide status feedback</li>
                  <li>✓ IR fallback ensures power-on works reliably</li>
                  <li>✓ Hybrid strategy gives best of both worlds</li>
                </ul>
              </div>
            </div>
          )}
        </div>

        {/* Actions */}
        <div className="mt-6 flex gap-3">
          {isEditing || !hasIRFallback ? (
            <>
              <button
                onClick={() => {
                  if (isEditing && hasIRFallback) {
                    setIsEditing(false);
                  } else {
                    onClose();
                  }
                }}
                disabled={saving}
                className="flex-1 rounded-md border border-slate-200 bg-white px-4 py-2 text-sm font-medium text-slate-700 shadow-sm transition hover:bg-slate-50 disabled:cursor-not-allowed disabled:opacity-50"
              >
                Cancel
              </button>
              <button
                onClick={handleSave}
                disabled={saving || availablePorts.length === 0}
                className="flex-1 rounded-md bg-brand-500 px-4 py-2 text-sm font-medium text-white shadow-sm transition hover:bg-brand-600 disabled:cursor-not-allowed disabled:opacity-50"
              >
                {saving ? 'Saving...' : hasIRFallback ? 'Save Changes' : 'Link IR Fallback'}
              </button>
            </>
          ) : (
            <>
              <button
                onClick={handleUnlink}
                disabled={saving}
                className="flex-1 rounded-md border border-red-200 bg-white px-4 py-2 text-sm font-medium text-red-700 shadow-sm transition hover:bg-red-50 disabled:cursor-not-allowed disabled:opacity-50"
              >
                {saving ? 'Removing...' : 'Remove IR Fallback'}
              </button>
              <button
                onClick={onClose}
                className="flex-1 rounded-md bg-brand-500 px-4 py-2 text-sm font-medium text-white shadow-sm transition hover:bg-brand-600"
              >
                Close
              </button>
            </>
          )}
        </div>
      </div>
    </div>
  );
};
