import { useMemo, useState } from 'react';
import { useManagedDevices } from '../hooks/use-managed-devices';
import { ControllerTable } from '../components/controller-table';
import type { ManagedDevice } from '@/types';
import { ControllerEditModal } from '../components/controller-edit-modal';

export const ControllersPage = () => {
  const { data, isLoading, isError, error, refetch, isFetching } = useManagedDevices();

  const controllers = useMemo(() => data ?? [], [data]);
  const [editingDevice, setEditingDevice] = useState<ManagedDevice | null>(null);
  const activePortCount = useMemo(
    () => controllers.reduce((count, controller) => count + controller.ir_ports.filter((port) => port.is_active).length, 0),
    [controllers],
  );

  return (
    <section className="space-y-6">
      <header className="flex items-center justify-between">
        <div>
          <h2 className="text-lg font-semibold text-slate-900">IR controllers</h2>
          <p className="text-sm text-slate-500">
            Monitor the hardware bridges that drive your venue devices. {controllers.length} controllers managing {activePortCount} ports.
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
          Loading managed devices…
        </div>
      ) : isError ? (
        <div className="rounded-lg border border-rose-200 bg-rose-50 p-4 text-sm text-rose-700">
          Failed to load devices. {error instanceof Error ? error.message : 'Please try again.'}
        </div>
      ) : (
        <ControllerTable controllers={controllers} onEdit={setEditingDevice} />
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
