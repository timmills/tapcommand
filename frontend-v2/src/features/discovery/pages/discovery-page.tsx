import { useState } from 'react';
import { DiscoveryTable } from '../components/discovery-table';
import { useDiscoveryControls, useDiscoveryDevices } from '../hooks/use-discovery';
import type { DiscoveredDevice } from '@/types';
import { ControllerEditModal } from '../../devices/components/controller-edit-modal';

export const DiscoveryPage = () => {
  const { data, isLoading, isError, error, isFetching, refetch } = useDiscoveryDevices();
  const { startDiscovery, stopDiscovery } = useDiscoveryControls();
  const [selectedDevice, setSelectedDevice] = useState<DiscoveredDevice | null>(null);

  return (
    <section className="space-y-6">
      <header className="flex flex-col gap-4 sm:flex-row sm:items-center sm:justify-between">
        <div>
          <h2 className="text-lg font-semibold text-slate-900">Network discovery</h2>
          <p className="text-sm text-slate-500">
            Trigger an mDNS sweep to locate ESPHome IR controllers that are not yet managed.
          </p>
        </div>
        <div className="flex items-center gap-2">
          <button
            type="button"
            onClick={() => startDiscovery.mutate()}
            disabled={startDiscovery.isPending}
            className="inline-flex items-center gap-1 rounded-md bg-brand-500 px-3 py-2 text-sm font-medium text-white shadow-sm transition hover:bg-brand-600 disabled:cursor-not-allowed disabled:bg-brand-300"
          >
            {startDiscovery.isPending ? 'Starting…' : 'Start discovery'}
          </button>
          <button
            type="button"
            onClick={() => stopDiscovery.mutate()}
            disabled={stopDiscovery.isPending}
            className="inline-flex items-center gap-1 rounded-md border border-slate-300 px-3 py-2 text-sm font-medium text-slate-700 transition hover:bg-slate-100 disabled:cursor-not-allowed disabled:opacity-60"
          >
            {stopDiscovery.isPending ? 'Stopping…' : 'Stop'}
          </button>
        </div>
      </header>

      {isLoading ? (
        <div className="flex items-center justify-center rounded-lg border border-dashed border-slate-300 bg-white p-8 text-sm text-slate-500">
          Loading discovery results…
        </div>
      ) : isError ? (
        <div className="rounded-lg border border-rose-200 bg-rose-50 p-4 text-sm text-rose-700">
          Failed to load discovery results. {error instanceof Error ? error.message : 'Please try again.'}
        </div>
      ) : (
        <DiscoveryTable devices={data ?? []} onSelect={setSelectedDevice} />
      )}

      {isFetching && !isLoading && (
        <div className="text-xs text-slate-500">Refreshing discovery data…</div>
      )}

      {selectedDevice ? (
        <ControllerEditModal
          open={Boolean(selectedDevice)}
          discovered={selectedDevice}
          onClose={() => setSelectedDevice(null)}
          onSaved={() => {
            setSelectedDevice(null);
            refetch();
          }}
        />
      ) : null}
    </section>
  );
};
