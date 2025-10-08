import { RefreshCw, Trash2, Speaker } from 'lucide-react';
import { useAudioControllers, useDeleteController, useRediscoverZones } from '../hooks/use-audio';
import { ZoneCard } from '../components/zone-card';
import { AmplifierInfoCards } from '../components/amplifier-info-cards';

export function AudioPage() {
  const { data: controllers, isLoading, isError, error } = useAudioControllers();
  const deleteController = useDeleteController();
  const rediscoverZones = useRediscoverZones();

  const handleDelete = (controllerId: string, controllerName: string) => {
    if (confirm(`Delete audio controller "${controllerName}"? This will remove all zones.`)) {
      deleteController.mutate(controllerId);
    }
  };

  const handleRediscover = (controllerId: string) => {
    rediscoverZones.mutate(controllerId);
  };

  return (
    <section className="space-y-6">
      {/* Page header */}
      <header>
        <h2 className="text-lg font-semibold text-slate-900">Audio Controllers</h2>
        <p className="text-sm text-slate-500">
          Manage audio amplifiers and zones
        </p>
      </header>

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
              Add a Bosch Praesensa or other AES70 amplifier from the Discovery page.
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
