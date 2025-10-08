import { useState, useEffect } from 'react';
import axios from 'axios';
import { BrandInfoCards } from '../components/brand-info-cards';
import { VirtualDeviceIRFallbackModal } from '@/features/devices/components/virtual-device-ir-fallback-modal';
import type { ManagedDevice } from '@/types/api';

interface DiscoveredTV {
  ip: string;
  name: string;
  model: string;
  mac: string;
  protocol: string;
  status: 'online' | 'offline' | 'unknown';
  device_type: string | null;
  vendor: string | null;
  ports: number[];
  confidence_score: number | null;
  confidence_reason: string | null;
  adoptable: 'ready' | 'needs_config' | 'unlikely';
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

interface VirtualController {
  id: number;
  controller_id: string;
  controller_name: string;
  controller_type: string;
  protocol: string;
  total_ports: number;
  is_online: boolean;
  fallback_ir_controller?: string;
  fallback_ir_port?: number;
  power_on_method?: string;
  control_strategy?: string;
}

interface AdoptionModalProps {
  tv: DiscoveredTV | null;
  isOpen: boolean;
  onClose: () => void;
  onAdopt: (ip: string, controllerName?: string) => Promise<void>;
}

const AdoptionModal = ({ tv, isOpen, onClose, onAdopt }: AdoptionModalProps) => {
  const [adopting, setAdopting] = useState(false);
  const [availableIRControllers, setAvailableIRControllers] = useState<ManagedDevice[]>([]);
  const [selectedIRController, setSelectedIRController] = useState<string>('');
  const [selectedIRPort, setSelectedIRPort] = useState<number>(1);
  const [linkIR, setLinkIR] = useState(false);
  const [controllerName, setControllerName] = useState('');

  useEffect(() => {
    if (isOpen && tv) {
      // Pre-fill controller name with TV name
      setControllerName(tv.name || '');

      // Load available IR controllers
      axios.get<ManagedDevice[]>('http://localhost:8000/api/v1/management/managed')
        .then(response => {
          const irControllers = response.data.filter(d => d.device_type === 'ir_controller');
          setAvailableIRControllers(irControllers);
          if (irControllers.length > 0) {
            setSelectedIRController(irControllers[0].hostname);
          }
        })
        .catch(error => console.error('Failed to load IR controllers:', error));
    }
  }, [isOpen, tv]);

  if (!isOpen || !tv) return null;

  const handleAdopt = async () => {
    setAdopting(true);
    try {
      await onAdopt(tv.ip, controllerName.trim() || undefined);

      // If user wants to link IR, do it after adoption
      if (linkIR && selectedIRController) {
        // Get the newly adopted virtual controller
        const vcsResponse = await axios.get('http://localhost:8000/api/virtual-controllers/');
        const newVC = vcsResponse.data.find((vc: any) => vc.controller_id.includes(tv.mac.slice(-6).toLowerCase()));

        if (newVC) {
          // Link IR fallback
          await axios.post(`http://localhost:8000/api/hybrid-devices/${newVC.id}/link-ir-fallback`, {
            ir_controller_hostname: selectedIRController,
            ir_port: selectedIRPort,
            power_on_method: 'hybrid',
            control_strategy: 'hybrid_ir_fallback'
          });
        }
      }

      onClose();
    } catch (error) {
      console.error('Adoption failed:', error);
    } finally {
      setAdopting(false);
    }
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/50">
      <div className="mx-4 w-full max-w-lg rounded-lg bg-white p-6 shadow-xl">
        <h3 className="text-lg font-semibold text-slate-900">Adopt TV as Virtual Controller</h3>

        <div className="mt-4 space-y-3">
          <div className="rounded-lg border border-slate-200 bg-slate-50 p-3">
            <div className="flex items-center gap-3">
              <div className="flex h-10 w-10 items-center justify-center rounded-lg bg-brand-100">
                <svg className="h-6 w-6 text-brand-600" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9.75 17L9 20l-1 1h8l-1-1-.75-3M3 13h18M5 17h14a2 2 0 002-2V5a2 2 0 00-2-2H5a2 2 0 00-2 2v10a2 2 0 002 2z" />
                </svg>
              </div>
              <div className="flex-1">
                <h4 className="font-medium text-slate-900">{tv.name}</h4>
                <p className="text-sm text-slate-500">{tv.ip} • {tv.vendor || 'Unknown'}</p>
              </div>
            </div>
          </div>

          <label className="flex flex-col text-sm font-medium text-slate-700">
            Controller Name
            <input
              type="text"
              value={controllerName}
              onChange={(e) => setControllerName(e.target.value)}
              placeholder="Enter a name for this controller"
              className="mt-1 rounded-md border border-slate-300 px-3 py-2 text-sm text-slate-900 shadow-sm focus:border-brand-500 focus:outline-none focus:ring-1 focus:ring-brand-500"
            />
            <span className="mt-1 text-xs text-slate-500">
              Give this virtual controller a friendly name (e.g., "Lobby TV", "Room 101")
            </span>
          </label>

          <div className="space-y-2 text-sm">
            <div className="flex justify-between">
              <span className="text-slate-600">Protocol:</span>
              <span className="font-medium text-slate-900">{tv.protocol || 'Unknown'}</span>
            </div>
            <div className="flex justify-between">
              <span className="text-slate-600">Device Type:</span>
              <span className="font-medium text-slate-900">{tv.device_type?.replace(/_/g, ' ') || 'Generic'}</span>
            </div>
            <div className="flex justify-between">
              <span className="text-slate-600">Confidence Score:</span>
              <span className="font-medium text-slate-900">{tv.confidence_score || 0}/100</span>
            </div>
            {tv.confidence_reason && (
              <div className="mt-2 rounded-md bg-blue-50 p-2 text-xs text-blue-700">
                {tv.confidence_reason}
              </div>
            )}
          </div>

          <div className="rounded-lg border border-blue-200 bg-blue-50 p-3">
            <h4 className="text-sm font-medium text-blue-900">What happens when you adopt?</h4>
            <ul className="mt-2 space-y-1 text-xs text-blue-700">
              <li>✓ Creates a Virtual Controller for this TV</li>
              <li>✓ Maps TV to port 1 of the controller</li>
              <li>✓ Enables control through SmartVenue</li>
              <li>✓ Removes from discovery list</li>
            </ul>
          </div>

          {availableIRControllers.length > 0 && (
            <div className="rounded-lg border border-amber-200 bg-amber-50 p-3">
              <div className="flex items-start gap-2">
                <input
                  type="checkbox"
                  id="link-ir"
                  checked={linkIR}
                  onChange={(e) => setLinkIR(e.target.checked)}
                  className="mt-0.5 h-4 w-4 rounded border-amber-300 text-brand-600 focus:ring-brand-500"
                />
                <div className="flex-1">
                  <label htmlFor="link-ir" className="text-sm font-medium text-amber-900 cursor-pointer">
                    Link IR Controller for Hybrid Control
                  </label>
                  <p className="mt-1 text-xs text-amber-700">
                    Recommended: Use IR for power-on, network for other commands
                  </p>
                </div>
              </div>

              {linkIR && (
                <div className="mt-3 space-y-3">
                  <div>
                    <label className="block text-xs font-medium text-amber-900">IR Controller</label>
                    <select
                      value={selectedIRController}
                      onChange={(e) => setSelectedIRController(e.target.value)}
                      className="mt-1 block w-full rounded-md border-amber-200 text-sm focus:border-brand-500 focus:ring-brand-500"
                    >
                      {availableIRControllers.map((controller) => (
                        <option key={controller.hostname} value={controller.hostname}>
                          {controller.hostname} ({controller.current_ip_address})
                        </option>
                      ))}
                    </select>
                  </div>
                  <div>
                    <label className="block text-xs font-medium text-amber-900">IR Port</label>
                    <input
                      type="number"
                      min="1"
                      max="8"
                      value={selectedIRPort}
                      onChange={(e) => setSelectedIRPort(parseInt(e.target.value))}
                      className="mt-1 block w-full rounded-md border-amber-200 text-sm focus:border-brand-500 focus:ring-brand-500"
                    />
                  </div>
                </div>
              )}
            </div>
          )}
        </div>

        <div className="mt-6 flex gap-3">
          <button
            onClick={onClose}
            disabled={adopting}
            className="flex-1 rounded-md border border-slate-200 bg-white px-4 py-2 text-sm font-medium text-slate-700 shadow-sm transition hover:bg-slate-50 disabled:cursor-not-allowed disabled:opacity-50"
          >
            Cancel
          </button>
          <button
            onClick={handleAdopt}
            disabled={adopting}
            className="flex-1 rounded-md bg-brand-500 px-4 py-2 text-sm font-medium text-white shadow-sm transition hover:bg-brand-600 disabled:cursor-not-allowed disabled:opacity-50"
          >
            {adopting ? 'Adopting...' : 'Adopt TV'}
          </button>
        </div>
      </div>
    </div>
  );
};

export const NetworkControllersPage = () => {
  const [tvs, setTvs] = useState<DiscoveredTV[]>([]);
  const [discovering, setDiscovering] = useState(false);
  const [commandInProgress, setCommandInProgress] = useState<string | null>(null);
  const [adoptionModal, setAdoptionModal] = useState<{ isOpen: boolean; tv: DiscoveredTV | null }>({
    isOpen: false,
    tv: null,
  });
  const [virtualControllers, setVirtualControllers] = useState<VirtualController[]>([]);
  const [virtualDevices, setVirtualDevices] = useState<VirtualDevice[]>([]);
  const [hidingDevice, setHidingDevice] = useState<string | null>(null);
  const [deletingController, setDeletingController] = useState<string | null>(null);
  const [unlinkingIR, setUnlinkingIR] = useState<number | null>(null);
  const [editingVirtualDevice, setEditingVirtualDevice] = useState<VirtualDevice | null>(null);

  const handleDiscover = async () => {
    setDiscovering(true);
    try {
      const response = await axios.get<DiscoveredTV[]>('http://localhost:8000/api/network-tv/discover', {
        timeout: 10000 // 10 second timeout for discovery
      });
      setTvs(response.data);
    } catch (error) {
      console.error('Discovery failed:', error);
    } finally {
      setDiscovering(false);
    }
  };

  const handleCommand = async (ip: string, command: string) => {
    setCommandInProgress(`${ip}-${command}`);
    try {
      await axios.post('http://localhost:8000/api/network-tv/command', {
        ip,
        command,
      });
    } catch (error) {
      console.error('Command failed:', error);
    } finally {
      setCommandInProgress(null);
    }
  };

  const handleAdopt = async (ip: string, controllerName?: string) => {
    try {
      const payload: Record<string, unknown> = {};
      if (controllerName) {
        payload['controller_name'] = controllerName;
      }
      await axios.post(`http://localhost:8000/api/network-tv/adopt/${ip}`, payload);
      // Refresh all lists
      await handleDiscover();
      await loadVirtualControllers();
      await loadVirtualDevices();
    } catch (error) {
      console.error('Adoption failed:', error);
      throw error;
    }
  };

  const loadVirtualControllers = async () => {
    try {
      const response = await axios.get<VirtualController[]>('http://localhost:8000/api/virtual-controllers/');
      setVirtualControllers(response.data);
    } catch (error) {
      console.error('Failed to load virtual controllers:', error);
    }
  };

  const loadVirtualDevices = async () => {
    try {
      const response = await axios.get<VirtualDevice[]>('http://localhost:8000/api/virtual-controllers/devices/all');
      setVirtualDevices(response.data);
    } catch (error) {
      console.error('Failed to load virtual devices:', error);
    }
  };

  const handleHideDevice = async (mac: string) => {
    setHidingDevice(mac);
    try {
      await axios.post(`http://localhost:8000/api/network-tv/hide/${mac}`);
      // Refresh discovery list
      await handleDiscover();
    } catch (error) {
      console.error('Failed to hide device:', error);
    } finally {
      setHidingDevice(null);
    }
  };

  const handleDeleteController = async (controllerId: string) => {
    if (!confirm(`Are you sure you want to delete this Virtual Controller? The device will return to the discovery pool.`)) {
      return;
    }

    setDeletingController(controllerId);
    try {
      await axios.delete(`http://localhost:8000/api/virtual-controllers/${controllerId}`);
      // Refresh all lists
      await loadVirtualControllers();
      await loadVirtualDevices();
      await handleDiscover();
    } catch (error) {
      console.error('Failed to delete controller:', error);
    } finally {
      setDeletingController(null);
    }
  };

  const handleUnlinkIR = async (deviceId: number) => {
    if (!confirm('Are you sure you want to remove the IR fallback for this TV?')) {
      return;
    }

    setUnlinkingIR(deviceId);
    try {
      await axios.delete(`http://localhost:8000/api/v1/hybrid-devices/${deviceId}/unlink-ir-fallback`);
      // Refresh virtual devices to show updated status
      await loadVirtualDevices();
    } catch (error) {
      console.error('Failed to unlink IR controller:', error);
    } finally {
      setUnlinkingIR(null);
    }
  };

  // Auto-discover on mount
  useEffect(() => {
    handleDiscover();
    loadVirtualControllers();
    loadVirtualDevices();
  }, []);

  const getAdoptableIcon = (adoptable: string) => {
    switch (adoptable) {
      case 'ready':
        return (
          <svg className="h-5 w-5 text-green-600" fill="none" viewBox="0 0 24 24" stroke="currentColor">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z" />
          </svg>
        );
      case 'needs_config':
        return (
          <svg className="h-5 w-5 text-yellow-600" fill="none" viewBox="0 0 24 24" stroke="currentColor">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z" />
          </svg>
        );
      default:
        return (
          <svg className="h-5 w-5 text-slate-400" fill="none" viewBox="0 0 24 24" stroke="currentColor">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M18.364 5.636a9 9 0 010 12.728m0 0l-2.829-2.829m2.829 2.829L21 21M15.536 8.464a5 5 0 010 7.072m0 0l-2.829-2.829m-4.243 2.829a4.978 4.978 0 01-1.414-2.83m-1.414 5.658a9 9 0 01-2.167-9.238m7.824 2.167a1 1 0 111.414 1.414m-1.414-1.414L3 3" />
          </svg>
        );
    }
  };

  const getAdoptableText = (adoptable: string) => {
    switch (adoptable) {
      case 'ready':
        return { text: 'Ready to Adopt', className: 'bg-green-50 text-green-700' };
      case 'needs_config':
        return { text: 'Needs Config', className: 'bg-yellow-50 text-yellow-700' };
      default:
        return { text: 'Unlikely TV', className: 'bg-slate-50 text-slate-700' };
    }
  };

  return (
    <section className="space-y-6">
      <header className="flex items-center justify-between">
        <div>
          <h2 className="text-lg font-semibold text-slate-900">TV Controllers</h2>
          <p className="text-sm text-slate-500">
            Discover and adopt network TVs. {tvs.filter(tv => tv.adoptable === 'ready').length} ready to adopt • {virtualControllers.length} adopted
          </p>
        </div>
        <button
          type="button"
          onClick={handleDiscover}
          disabled={discovering}
          className="inline-flex items-center gap-1 rounded-md bg-brand-500 px-3 py-2 text-sm font-medium text-white shadow-sm transition hover:bg-brand-600 disabled:cursor-not-allowed disabled:bg-brand-300"
        >
          {discovering ? (
            <>
              <svg className="h-4 w-4 animate-spin" fill="none" viewBox="0 0 24 24">
                <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" />
                <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z" />
              </svg>
              Discovering...
            </>
          ) : (
            'Discover TVs'
          )}
        </button>
      </header>

      {/* Discovered TVs Section - MOVED TO TOP */}
      <div className="space-y-3">
        <h3 className="text-sm font-medium text-slate-900">Discovered Devices</h3>
        {tvs.length === 0 && !discovering && (
          <div className="rounded-lg border border-slate-200 bg-slate-50 p-8 text-center">
            <svg className="mx-auto h-12 w-12 text-slate-400" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9.75 17L9 20l-1 1h8l-1-1-.75-3M3 13h18M5 17h14a2 2 0 002-2V5a2 2 0 00-2-2H5a2 2 0 00-2 2v10a2 2 0 002 2z" />
            </svg>
            <h3 className="mt-2 text-sm font-medium text-slate-900">No devices discovered</h3>
            <p className="mt-1 text-sm text-slate-500">Click "Discover TVs" to scan your network</p>
          </div>
        )}

        {tvs.map((tv) => {
          const adoptableStatus = getAdoptableText(tv.adoptable);

          return (
            <div key={tv.ip} className="rounded-lg border border-slate-200 bg-white p-4 shadow-sm">
              <div className="flex items-center justify-between">
                <div className="flex items-center gap-3">
                  {getAdoptableIcon(tv.adoptable)}
                  <div>
                    <h4 className="font-medium text-slate-900">{tv.name}</h4>
                    <p className="text-sm text-slate-500">
                      {tv.ip} • {tv.vendor || 'Unknown'} • Score: {tv.confidence_score || 0}/100
                    </p>
                  </div>
                </div>
                <div className="flex items-center gap-2">
                  <span className={`inline-flex items-center gap-1 rounded-full px-2 py-1 text-xs font-medium ${adoptableStatus.className}`}>
                    {adoptableStatus.text}
                  </span>
                  {/* Hide Button */}
                  <button
                    onClick={() => handleHideDevice(tv.mac)}
                    disabled={hidingDevice === tv.mac}
                    className="inline-flex items-center gap-1 rounded-md border border-slate-200 bg-white px-3 py-1.5 text-sm font-medium text-slate-700 shadow-sm transition hover:bg-slate-50 disabled:cursor-not-allowed disabled:opacity-50"
                    title="Hide this device"
                  >
                    <svg className="h-4 w-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M13.875 18.825A10.05 10.05 0 0112 19c-4.478 0-8.268-2.943-9.543-7a9.97 9.97 0 011.563-3.029m5.858.908a3 3 0 114.243 4.243M9.878 9.878l4.242 4.242M9.88 9.88l-3.29-3.29m7.532 7.532l3.29 3.29M3 3l3.59 3.59m0 0A9.953 9.953 0 0112 5c4.478 0 8.268 2.943 9.543 7a10.025 10.025 0 01-4.132 5.411m0 0L21 21" />
                    </svg>
                    {hidingDevice === tv.mac ? 'Hiding...' : 'Hide'}
                  </button>
                  {tv.adoptable === 'ready' && (
                    <button
                      onClick={() => setAdoptionModal({ isOpen: true, tv })}
                      className="inline-flex items-center gap-1 rounded-md bg-brand-500 px-3 py-1.5 text-sm font-medium text-white shadow-sm transition hover:bg-brand-600"
                    >
                      <svg className="h-4 w-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 4v16m8-8H4" />
                      </svg>
                      Adopt
                    </button>
                  )}
                </div>
              </div>

              {tv.confidence_reason && (
                <div className="mt-3 rounded-md bg-slate-50 p-2 text-xs text-slate-600">
                  {tv.confidence_reason}
                </div>
              )}

              {tv.adoptable === 'needs_config' && (
                <div className="mt-3 rounded-md bg-yellow-50 p-3 text-sm text-yellow-800">
                  <p className="font-medium">Configuration Needed</p>
                  <p className="mt-1 text-xs">Enable network control in TV settings, then re-scan to adopt.</p>
                </div>
              )}

              {tv.status === 'online' && tv.protocol && (
                <div className="mt-4 flex gap-2">
                  <button
                    onClick={() => handleCommand(tv.ip, 'power')}
                    disabled={commandInProgress === `${tv.ip}-power`}
                    className="inline-flex items-center gap-1 rounded-md border border-slate-200 bg-white px-3 py-1.5 text-sm font-medium text-slate-700 shadow-sm transition hover:bg-slate-50 disabled:cursor-not-allowed disabled:opacity-50"
                  >
                    <svg className="h-4 w-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M13 10V3L4 14h7v7l9-11h-7z" />
                    </svg>
                    Test Power
                  </button>
                  <button
                    onClick={() => handleCommand(tv.ip, 'volume_up')}
                    disabled={commandInProgress === `${tv.ip}-volume_up`}
                    className="inline-flex items-center gap-1 rounded-md border border-slate-200 bg-white px-3 py-1.5 text-sm font-medium text-slate-700 shadow-sm transition hover:bg-slate-50 disabled:cursor-not-allowed disabled:opacity-50"
                  >
                    <svg className="h-4 w-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15.536 8.464a5 5 0 010 7.072m2.828-9.9a9 9 0 010 12.728M5.586 15H4a1 1 0 01-1-1v-4a1 1 0 011-1h1.586l4.707-4.707C10.923 3.663 12 4.109 12 5v14c0 .891-1.077 1.337-1.707.707L5.586 15z" />
                    </svg>
                    Test Vol+
                  </button>
                </div>
              )}
            </div>
          );
        })}
      </div>

      <div className="rounded-lg border border-slate-200 bg-white p-4 shadow-sm">
        <BrandInfoCards />
      </div>

      {/* Virtual Controllers Section - MOVED TO BOTTOM */}
      {virtualControllers.length > 0 && (
        <div className="space-y-3">
          <h3 className="text-sm font-medium text-slate-900">Adopted Virtual Controllers</h3>
          <p className="text-xs text-slate-500">
            These TVs have been adopted and can be controlled through the Management page
          </p>
          {virtualControllers.map((vc) => {
            // Find the Virtual Device for this controller (port 1)
            const virtualDevice = virtualDevices.find(vd => vd.controller_id === vc.id && vd.port_number === 1);

            return (
              <div key={vc.id} className="rounded-lg border border-green-200 bg-green-50 p-4">
                <div className="flex items-center justify-between">
                  <div className="flex items-center gap-3">
                    <div className="flex h-10 w-10 items-center justify-center rounded-lg bg-green-100">
                      <svg className="h-6 w-6 text-green-600" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 13l4 4L19 7" />
                      </svg>
                    </div>
                    <div>
                      <h4 className="font-medium text-green-900">{vc.controller_name}</h4>
                      <p className="text-sm text-green-700">{vc.controller_id} • {vc.protocol}</p>
                      {virtualDevice?.fallback_ir_controller && (
                        <p className="text-xs text-green-600 mt-1">
                          🔌 IR Fallback: {virtualDevice.fallback_ir_controller} (Port {virtualDevice.fallback_ir_port})
                        </p>
                      )}
                    </div>
                  </div>
                  <div className="flex items-center gap-2">
                    <span className={`inline-flex items-center gap-1 rounded-full px-2 py-1 text-xs font-medium ${
                      vc.is_online ? 'bg-green-100 text-green-700' : 'bg-slate-100 text-slate-700'
                    }`}>
                      <svg className="h-3 w-3" fill="currentColor" viewBox="0 0 8 8">
                        <circle cx="4" cy="4" r="3" />
                      </svg>
                      {vc.is_online ? 'Online' : 'Offline'}
                    </span>
                    {/* Edit Port / Configure IR Button */}
                    {virtualDevice && (
                      <button
                        onClick={() => setEditingVirtualDevice(virtualDevice)}
                        className="inline-flex items-center gap-1 rounded-md border border-blue-200 bg-white px-3 py-1.5 text-sm font-medium text-blue-700 shadow-sm transition hover:bg-blue-50"
                        title="Configure IR Fallback"
                      >
                        <svg className="h-4 w-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M10.325 4.317c.426-1.756 2.924-1.756 3.35 0a1.724 1.724 0 002.573 1.066c1.543-.94 3.31.826 2.37 2.37a1.724 1.724 0 001.065 2.572c1.756.426 1.756 2.924 0 3.35a1.724 1.724 0 00-1.066 2.573c.94 1.543-.826 3.31-2.37 2.37a1.724 1.724 0 00-2.572 1.065c-.426 1.756-2.924 1.756-3.35 0a1.724 1.724 0 00-2.573-1.066c-1.543.94-3.31-.826-2.37-2.37a1.724 1.724 0 00-1.065-2.572c-1.756-.426-1.756-2.924 0-3.35a1.724 1.724 0 001.066-2.573c-.94-1.543.826-3.31 2.37-2.37.996.608 2.296.07 2.572-1.065z" />
                          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15 12a3 3 0 11-6 0 3 3 0 016 0z" />
                        </svg>
                        {virtualDevice.fallback_ir_controller ? 'Edit IR' : 'Link IR'}
                      </button>
                    )}
                    {/* Delete Button */}
                    <button
                      onClick={() => handleDeleteController(vc.controller_id)}
                      disabled={deletingController === vc.controller_id}
                      className="inline-flex items-center gap-1 rounded-md border border-red-200 bg-white px-3 py-1.5 text-sm font-medium text-red-700 shadow-sm transition hover:bg-red-50 disabled:cursor-not-allowed disabled:opacity-50"
                      title="Delete this Virtual Controller"
                    >
                      <svg className="h-4 w-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1 1v3M4 7h16" />
                      </svg>
                      {deletingController === vc.controller_id ? 'Deleting...' : 'Delete'}
                    </button>
                  </div>
                </div>
              </div>
            );
          })}
        </div>
      )}

      <AdoptionModal
        tv={adoptionModal.tv}
        isOpen={adoptionModal.isOpen}
        onClose={() => setAdoptionModal({ isOpen: false, tv: null })}
        onAdopt={handleAdopt}
      />

      <VirtualDeviceIRFallbackModal
        device={editingVirtualDevice}
        open={Boolean(editingVirtualDevice)}
        onClose={() => setEditingVirtualDevice(null)}
        onSaved={() => {
          setEditingVirtualDevice(null);
          loadVirtualDevices();
        }}
      />
    </section>
  );
};
