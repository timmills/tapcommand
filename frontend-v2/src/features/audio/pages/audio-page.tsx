import { RefreshCw, Trash2, Speaker, Plus } from 'lucide-react';
import { useState } from 'react';
import { useAudioControllers, useDeleteController, useRediscoverZones, useAddController } from '../hooks/use-audio';
import { ZoneCard } from '../components/zone-card';
import { AmplifierInfoCards } from '../components/amplifier-info-cards';
import { PresetButtons } from '../components/preset-buttons';

export function AudioPage() {
  const { data: controllers, isLoading, isError, error } = useAudioControllers();
  const deleteController = useDeleteController();
  const rediscoverZones = useRediscoverZones();
  const addController = useAddController();

  const [showManualEntry, setShowManualEntry] = useState(false);
  const [manualIP, setManualIP] = useState('');
  const [manualName, setManualName] = useState('');
  const [manualProtocol, setManualProtocol] = useState<'bosch_aes70' | 'bosch_plena_matrix'>('bosch_aes70');
  const [manualPort, setManualPort] = useState('65000');
  const [manualZones, setManualZones] = useState('4');

  const handleDelete = (controllerId: string, controllerName: string) => {
    if (confirm(`Delete audio controller "${controllerName}"? This will remove all zones.`)) {
      deleteController.mutate(controllerId);
    }
  };

  const handleRediscover = (controllerId: string) => {
    rediscoverZones.mutate(controllerId);
  };

  const handleManualAdd = () => {
    if (!manualIP || !manualName) {
      alert('Please enter both IP address and controller name');
      return;
    }

    const payload: any = {
      ip_address: manualIP,
      controller_name: manualName,
      protocol: manualProtocol,
    };

    // Add port if specified
    if (manualPort) {
      payload.port = parseInt(manualPort);
    }

    // Add total_zones for Plena Matrix
    if (manualProtocol === 'bosch_plena_matrix' && manualZones) {
      payload.total_zones = parseInt(manualZones);
    }

    addController.mutate(payload, {
      onSuccess: () => {
        setManualIP('');
        setManualName('');
        setManualProtocol('bosch_aes70');
        setManualPort('65000');
        setManualZones('4');
        setShowManualEntry(false);
      },
    });
  };

  return (
    <section className="space-y-6">
      {/* Page header */}
      <header className="flex items-center justify-between">
        <div>
          <h2 className="text-lg font-semibold text-slate-900">Audio Controllers</h2>
          <p className="text-sm text-slate-500">
            Manage audio amplifiers and zones
          </p>
        </div>
        <button
          onClick={() => setShowManualEntry(!showManualEntry)}
          className="inline-flex items-center gap-2 rounded-md bg-brand-500 px-4 py-2 text-sm font-medium text-white shadow-sm transition hover:bg-brand-600"
        >
          <Plus className="h-4 w-4" />
          Add Manual IP
        </button>
      </header>

      {/* Manual entry form */}
      {showManualEntry && (
        <div className="rounded-lg border border-slate-200 bg-white p-4 shadow-sm">
          <h3 className="text-sm font-semibold text-slate-900 mb-3">Add Audio Controller Manually</h3>
          <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-5">
            <div>
              <label className="block text-sm font-medium text-slate-700 mb-1">
                Protocol
              </label>
              <select
                value={manualProtocol}
                onChange={(e) => {
                  const protocol = e.target.value as 'bosch_aes70' | 'bosch_plena_matrix';
                  setManualProtocol(protocol);
                  // Update default port based on protocol
                  setManualPort(protocol === 'bosch_aes70' ? '65000' : '12128');
                }}
                className="w-full rounded-md border border-slate-300 px-3 py-2 text-sm shadow-sm focus:border-brand-500 focus:outline-none focus:ring-1 focus:ring-brand-500"
              >
                <option value="bosch_aes70">Bosch Praesensa (AES70)</option>
                <option value="bosch_plena_matrix">Bosch Plena Matrix (UDP)</option>
              </select>
            </div>
            <div>
              <label className="block text-sm font-medium text-slate-700 mb-1">
                IP Address
              </label>
              <input
                type="text"
                value={manualIP}
                onChange={(e) => setManualIP(e.target.value)}
                placeholder="192.168.1.100"
                className="w-full rounded-md border border-slate-300 px-3 py-2 text-sm shadow-sm focus:border-brand-500 focus:outline-none focus:ring-1 focus:ring-brand-500"
              />
            </div>
            <div>
              <label className="block text-sm font-medium text-slate-700 mb-1">
                Controller Name
              </label>
              <input
                type="text"
                value={manualName}
                onChange={(e) => setManualName(e.target.value)}
                placeholder={manualProtocol === 'bosch_aes70' ? 'Bosch Praesensa' : 'Plena Matrix'}
                className="w-full rounded-md border border-slate-300 px-3 py-2 text-sm shadow-sm focus:border-brand-500 focus:outline-none focus:ring-1 focus:ring-brand-500"
              />
            </div>
            <div>
              <label className="block text-sm font-medium text-slate-700 mb-1">
                Port
              </label>
              <input
                type="text"
                value={manualPort}
                onChange={(e) => setManualPort(e.target.value)}
                placeholder={manualProtocol === 'bosch_aes70' ? '65000' : '12128'}
                className="w-full rounded-md border border-slate-300 px-3 py-2 text-sm shadow-sm focus:border-brand-500 focus:outline-none focus:ring-1 focus:ring-brand-500"
              />
            </div>
            {manualProtocol === 'bosch_plena_matrix' && (
              <div>
                <label className="block text-sm font-medium text-slate-700 mb-1">
                  Zones
                </label>
                <input
                  type="text"
                  value={manualZones}
                  onChange={(e) => setManualZones(e.target.value)}
                  placeholder="4"
                  className="w-full rounded-md border border-slate-300 px-3 py-2 text-sm shadow-sm focus:border-brand-500 focus:outline-none focus:ring-1 focus:ring-brand-500"
                />
              </div>
            )}
          </div>
          <div className="mt-4 flex gap-2">
            <button
              onClick={handleManualAdd}
              disabled={addController.isPending}
              className="rounded-md bg-brand-500 px-4 py-2 text-sm font-medium text-white shadow-sm transition hover:bg-brand-600 disabled:cursor-not-allowed disabled:opacity-50"
            >
              {addController.isPending ? 'Adding...' : 'Add Controller'}
            </button>
            <button
              onClick={() => setShowManualEntry(false)}
              className="rounded-md border border-slate-300 bg-white px-4 py-2 text-sm font-medium text-slate-700 shadow-sm transition hover:bg-slate-50"
            >
              Cancel
            </button>
          </div>
        </div>
      )}

      {/* Loading state */}
      {isLoading && (
        <div className="flex items-center justify-center rounded-lg border border-dashed border-slate-300 bg-white p-8 text-sm text-slate-500">
          Loading audio controllers…
        </div>
      )}

      {/* Error state */}
      {isError && (
        <div className="rounded-lg border border-rose-200 bg-rose-50 p-4 text-sm text-rose-700">
          Failed to load audio controllers.{' '}
          {error instanceof Error ? error.message : 'Please try again.'}
        </div>
      )}

      {/* Empty state */}
      {!isLoading && !isError && (!controllers || controllers.length === 0) && (
        <div className="rounded-lg border border-dashed border-slate-300 bg-white p-8">
          <div className="flex flex-col items-center text-center">
            <Speaker className="h-12 w-12 text-slate-300" />
            <h3 className="mt-2 text-sm font-medium text-slate-900">
              No audio controllers
            </h3>
            <p className="mt-1 text-sm text-slate-500">
              Click "Add Manual IP" to add an audio controller.
            </p>
          </div>
        </div>
      )}

      {/* Controllers and zones */}
      {!isLoading && !isError && controllers && controllers.length > 0 && (
        <div className="space-y-8">
          {controllers.map((controller) => (
            <div key={controller.id} className="space-y-4">
              {/* Controller header */}
              <div className="flex items-start justify-between rounded-lg border border-slate-200 bg-slate-50 p-4">
                <div className="flex-1">
                  <h3 className="font-semibold text-slate-900">
                    {controller.controller_name}
                  </h3>
                  <p className="mt-1 text-sm text-slate-500">
                    {controller.ip_address}:{controller.port} •{' '}
                    {controller.total_zones} zone{controller.total_zones !== 1 ? 's' : ''}
                  </p>
                  <div className="mt-2 flex items-center gap-2">
                    <div
                      className={`rounded-full px-2 py-0.5 text-xs font-medium ${
                        controller.is_online
                          ? 'bg-emerald-50 text-emerald-700'
                          : 'bg-slate-100 text-slate-600'
                      }`}
                    >
                      {controller.is_online ? 'Online' : 'Offline'}
                    </div>
                    <span className="text-xs text-slate-400">
                      {controller.controller_type} • {controller.controller_id}
                    </span>
                  </div>
                </div>

                {/* Controller actions */}
                <div className="flex gap-2">
                  <button
                    onClick={() => handleRediscover(controller.controller_id)}
                    disabled={rediscoverZones.isPending}
                    className="inline-flex items-center gap-1 rounded-md border border-slate-300 px-3 py-1.5 text-sm font-medium text-slate-700 transition hover:bg-white disabled:cursor-not-allowed disabled:opacity-50"
                    title="Rediscover zones"
                  >
                    <RefreshCw className="h-3.5 w-3.5" />
                    Rediscover
                  </button>
                  <button
                    onClick={() => handleDelete(controller.controller_id, controller.controller_name)}
                    disabled={deleteController.isPending}
                    className="inline-flex items-center gap-1 rounded-md border border-rose-300 px-3 py-1.5 text-sm font-medium text-rose-700 transition hover:bg-rose-50 disabled:cursor-not-allowed disabled:opacity-50"
                    title="Delete controller"
                  >
                    <Trash2 className="h-3.5 w-3.5" />
                  </button>
                </div>
              </div>

              {/* Zones grid */}
              {controller.zones && controller.zones.length > 0 ? (
                <div className="grid grid-cols-1 gap-4 md:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4">
                  {controller.zones.map((zone) => (
                    <ZoneCard key={zone.id} zone={zone} />
                  ))}
                </div>
              ) : (
                <div className="rounded-lg border border-dashed border-slate-300 bg-white p-4 text-center text-sm text-slate-500">
                  No zones discovered for this controller
                </div>
              )}

              {/* Presets section (only for Plena Matrix) */}
              <PresetButtons
                controllerId={controller.controller_id}
                controllerName={controller.controller_name}
              />
            </div>
          ))}
        </div>
      )}

      {/* Supported Amplifiers Section */}
      <div className="rounded-lg border border-slate-200 bg-white p-4 shadow-sm">
        <AmplifierInfoCards />
      </div>
    </section>
  );
}
