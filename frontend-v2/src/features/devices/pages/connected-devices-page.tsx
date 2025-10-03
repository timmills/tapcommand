import { useState } from 'react';
import { useManagedDevices } from '../hooks/use-managed-devices';
import { ConnectedDevicesTable } from '../components/connected-devices-table';
import type { ManagedDevice } from '@/types';
import { ControllerEditModal } from '../components/controller-edit-modal';
import { useDeviceTags } from '@/features/settings/hooks/use-device-tags';

export const ConnectedDevicesPage = () => {
  const { data, isLoading, isError, error, refetch, isFetching } = useManagedDevices();
  const { data: tags = [] } = useDeviceTags();
  const controllers = data ?? [];
  const [editingDevice, setEditingDevice] = useState<ManagedDevice | null>(null);

  return (
    <section className="space-y-6">
      <header className="flex items-center justify-between">
        <div>
          <h2 className="text-lg font-semibold text-slate-900">Connected devices</h2>
          <p className="text-sm text-slate-500">
            View the TVs and other equipment wired to each IR controller port. Assignments update when controllers sync.
          </p>
        </div>
        <button
          type="button"
          onClick={() => refetch()}
          disabled={isFetching}
          className="inline-flex items-center gap-1 rounded-md bg-brand-500 px-3 py-2 text-sm font-medium text-white shadow-sm transition hover:bg-brand-600 disabled:cursor-not-allowed disabled:bg-brand-300"
        >
          {isFetching ? 'Refreshing…' : 'Refresh'}
        </button>
      </header>

      {isLoading ? (
        <div className="flex items-center justify-center rounded-lg border border-dashed border-slate-300 bg-white p-8 text-sm text-slate-500">
          Loading connected devices…
        </div>
      ) : isError ? (
        <div className="rounded-lg border border-rose-200 bg-rose-50 p-4 text-sm text-rose-700">
          Failed to load connected devices. {error instanceof Error ? error.message : 'Please try again.'}
        </div>
      ) : (
        <ConnectedDevicesTable controllers={controllers} tags={tags} onEditController={setEditingDevice} />
      )}

      {editingDevice ? (
        <ControllerEditModal
          device={editingDevice}
          open={Boolean(editingDevice)}
          onClose={() => setEditingDevice(null)}
          onSaved={() => {
            setEditingDevice(null);
            refetch();
          }}
        />
      ) : null}
    </section>
  );
};
