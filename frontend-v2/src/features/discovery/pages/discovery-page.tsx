import { useState } from 'react';
import { useQuery } from '@tanstack/react-query';
import { DiscoveryTable } from '../components/discovery-table';
import { useDiscoveryControls } from '../hooks/use-discovery';
import { fetchAllDevices, type AllDevicesFilters } from '../api/discovery-api';
import type { DiscoveredDevice } from '@/types';
import { ControllerEditModal } from '../../devices/components/controller-edit-modal';

export const DiscoveryPage = () => {
  const { startDiscovery, stopDiscovery } = useDiscoveryControls();
  const [selectedDevice, setSelectedDevice] = useState<DiscoveredDevice | null>(null);

  // Filter states
  const [showESPHome, setShowESPHome] = useState(true);
  const [showNetwork, setShowNetwork] = useState(false);
  const [showManaged, setShowManaged] = useState(false);
  const [showHidden, setShowHidden] = useState(false);

  // Build filters object
  const filters: AllDevicesFilters = {
    show_esphome: showESPHome,
    show_network: showNetwork,
    show_managed: showManaged,
    show_hidden: showHidden,
  };

  // Fetch devices with filters
  const { data, isLoading, isError, error, isFetching, refetch } = useQuery({
    queryKey: ['all-devices', filters],
    queryFn: () => fetchAllDevices(filters),
    refetchInterval: 5000, // Auto-refresh every 5 seconds
  });

  return (
    <section className="space-y-6">
      <header className="flex flex-col gap-4 sm:flex-row sm:items-center sm:justify-between">
        <div>
          <h2 className="text-lg font-semibold text-slate-900">Network discovery</h2>
          <p className="text-sm text-slate-500">
            Discover ESPHome IR controllers and network devices.
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

      {/* Filter Controls */}
      <div className="rounded-lg border border-slate-200 bg-white p-4">
        <h3 className="text-sm font-medium text-slate-900 mb-3">Device Filters</h3>
        <div className="flex flex-wrap gap-4">
          <label className="flex items-center gap-2 cursor-pointer">
            <input
              type="checkbox"
              checked={showESPHome}
              onChange={(e) => setShowESPHome(e.target.checked)}
              className="rounded border-slate-300 text-brand-600 focus:ring-brand-500"
            />
            <span className="text-sm text-slate-700">
              ESPHome Devices {!showManaged && '(unadopted)'}
            </span>
          </label>

          <label className="flex items-center gap-2 cursor-pointer">
            <input
              type="checkbox"
              checked={showNetwork}
              onChange={(e) => setShowNetwork(e.target.checked)}
              className="rounded border-slate-300 text-brand-600 focus:ring-brand-500"
            />
            <span className="text-sm text-slate-700">
              Network Scan Devices
            </span>
          </label>

          <label className="flex items-center gap-2 cursor-pointer">
            <input
              type="checkbox"
              checked={showManaged}
              onChange={(e) => setShowManaged(e.target.checked)}
              className="rounded border-slate-300 text-brand-600 focus:ring-brand-500"
            />
            <span className="text-sm text-slate-700">
              Show Managed Devices
            </span>
          </label>

          <label className="flex items-center gap-2 cursor-pointer">
            <input
              type="checkbox"
              checked={showHidden}
              onChange={(e) => setShowHidden(e.target.checked)}
              className="rounded border-slate-300 text-brand-600 focus:ring-brand-500"
            />
            <span className="text-sm text-slate-700">
              Show Hidden Devices
            </span>
          </label>
        </div>
        <p className="text-xs text-slate-500 mt-2">
          {!showESPHome && !showNetwork ? (
            <span className="text-amber-600">⚠ No device types selected</span>
          ) : (
            <>
              Showing: {[
                showESPHome && 'ESPHome',
                showNetwork && 'Network Scan',
                showManaged && '(including managed)',
                showHidden && '(including hidden)'
              ].filter(Boolean).join(', ')}
            </>
          )}
        </p>
      </div>

      {isLoading ? (
        <div className="flex items-center justify-center rounded-lg border border-dashed border-slate-300 bg-white p-8 text-sm text-slate-500">
          Loading discovery results…
        </div>
      ) : isError ? (
        <div className="rounded-lg border border-rose-200 bg-rose-50 p-4 text-sm text-rose-700">
          Failed to load discovery results. {error instanceof Error ? error.message : 'Please try again.'}
        </div>
      ) : (
        <>
          <div className="text-sm text-slate-600">
            Found {data?.length ?? 0} device{data?.length !== 1 ? 's' : ''}
          </div>
          <DiscoveryTable devices={data ?? []} onSelect={setSelectedDevice} />
        </>
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
