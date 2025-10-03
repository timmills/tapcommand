import { useState } from 'react';
import { useSchedules, useDeleteSchedule, useToggleSchedule, useRunScheduleNow } from '../hooks/use-schedules';
import { formatNextRun, useCountdown } from '../hooks/use-countdown';
import { cronToHuman } from '../utils/cron-utils';
import { ScheduleFormModal } from '../components/schedule-form-modal';
import type { Schedule } from '../types/schedule';

export function SchedulesPage() {
  const [activeOnly, setActiveOnly] = useState(false);
  const [isModalOpen, setIsModalOpen] = useState(false);
  const [editingSchedule, setEditingSchedule] = useState<Schedule | undefined>();
  const { data, isLoading, error } = useSchedules({ active_only: activeOnly });
  const deleteSchedule = useDeleteSchedule();
  const toggleSchedule = useToggleSchedule();
  const runNow = useRunScheduleNow();

  const openCreateModal = () => {
    setEditingSchedule(undefined);
    setIsModalOpen(true);
  };

  const openEditModal = (schedule: Schedule) => {
    setEditingSchedule(schedule);
    setIsModalOpen(true);
  };

  const closeModal = () => {
    setIsModalOpen(false);
    setEditingSchedule(undefined);
  };

  if (isLoading) {
    return (
      <div className="flex h-64 items-center justify-center">
        <div className="text-lg text-slate-600">Loading schedules...</div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="rounded-lg border border-red-200 bg-red-50 p-4">
        <h3 className="font-semibold text-red-800">Error loading schedules</h3>
        <p className="text-sm text-red-600">{(error as Error).message}</p>
      </div>
    );
  }

  const schedules = data?.schedules || [];

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-3xl font-bold text-slate-900">Schedules</h1>
          <p className="mt-1 text-sm text-slate-600">
            Manage automated device schedules
          </p>
        </div>
        <button
          type="button"
          onClick={openCreateModal}
          className="rounded-lg bg-brand-600 px-4 py-2 text-sm font-semibold text-white shadow-sm hover:bg-brand-700"
        >
          + Create Schedule
        </button>
      </div>

      {/* Next Schedule Banner */}
      {schedules.length > 0 && schedules[0].next_run && (
        <NextScheduleBanner
          schedule={schedules[0]}
          onEdit={() => openEditModal(schedules[0])}
          onRunNow={() => runNow.mutate(schedules[0].id)}
        />
      )}

      {/* Filters */}
      <div className="flex items-center gap-4">
        <label className="flex items-center gap-2">
          <input
            type="checkbox"
            checked={activeOnly}
            onChange={(e) => setActiveOnly(e.target.checked)}
            className="h-4 w-4 rounded border-slate-300 text-brand-600 focus:ring-brand-500"
          />
          <span className="text-sm text-slate-700">Active only</span>
        </label>
        <div className="text-sm text-slate-500">
          Showing {schedules.length} of {data?.total || 0} schedules
        </div>
      </div>

      {/* Schedules Table */}
      {schedules.length === 0 ? (
        <div className="rounded-lg border-2 border-dashed border-slate-200 p-12 text-center">
          <p className="text-lg font-medium text-slate-900">No schedules yet</p>
          <p className="mt-1 text-sm text-slate-600">
            Create your first schedule to automate device actions
          </p>
          <button
            type="button"
            onClick={openCreateModal}
            className="mt-4 rounded-lg bg-brand-600 px-4 py-2 text-sm font-semibold text-white shadow-sm hover:bg-brand-700"
          >
            + Create Schedule
          </button>
        </div>
      ) : (
        <div className="overflow-hidden rounded-lg border border-slate-200 bg-white shadow-sm">
          <table className="min-w-full divide-y divide-slate-200">
            <thead className="bg-slate-50">
              <tr>
                <th className="px-4 py-3 text-left text-xs font-semibold uppercase tracking-wide text-slate-500">
                  Active
                </th>
                <th className="px-4 py-3 text-left text-xs font-semibold uppercase tracking-wide text-slate-500">
                  Name
                </th>
                <th className="px-4 py-3 text-left text-xs font-semibold uppercase tracking-wide text-slate-500">
                  Schedule
                </th>
                <th className="px-4 py-3 text-left text-xs font-semibold uppercase tracking-wide text-slate-500">
                  Next Run
                </th>
                <th className="px-4 py-3 text-left text-xs font-semibold uppercase tracking-wide text-slate-500">
                  Targets
                </th>
                <th className="px-4 py-3 text-right text-xs font-semibold uppercase tracking-wide text-slate-500">
                  Actions
                </th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-100">
              {schedules.map((schedule) => (
                <ScheduleRow
                  key={schedule.id}
                  schedule={schedule}
                  onToggle={() => toggleSchedule.mutate(schedule.id)}
                  onEdit={() => openEditModal(schedule)}
                  onDelete={async () => {
                    await deleteSchedule.mutateAsync(schedule.id);
                  }}
                />
              ))}
            </tbody>
          </table>
        </div>
      )}

      {/* Schedule Form Modal */}
      <ScheduleFormModal
        isOpen={isModalOpen}
        onClose={closeModal}
        schedule={editingSchedule}
      />
    </div>
  );
}

function NextScheduleBanner({ schedule, onEdit, onRunNow }: { schedule: Schedule; onEdit: () => void; onRunNow: () => void }) {
  const countdown = useCountdown(schedule.next_run);

  return (
    <div className="rounded-lg border border-blue-200 bg-blue-50 p-4">
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-3">
          <div className="text-2xl">🔔</div>
          <div>
            <div className="font-semibold text-blue-900">Next Scheduled Action</div>
            <div className="text-sm text-blue-700">
              "{schedule.name}" runs in {countdown} ({formatNextRun(schedule.next_run)})
            </div>
          </div>
        </div>
        <div className="flex gap-2">
          <button
            onClick={onEdit}
            className="rounded-md border border-blue-300 bg-white px-3 py-1.5 text-sm font-medium text-blue-700 hover:bg-blue-50"
          >
            Edit
          </button>
          <button
            onClick={onRunNow}
            className="rounded-md bg-blue-600 px-3 py-1.5 text-sm font-medium text-white hover:bg-blue-700"
          >
            Run Now
          </button>
        </div>
      </div>
    </div>
  );
}

function ScheduleRow({
  schedule,
  onToggle,
  onDelete,
  onEdit,
}: {
  schedule: Schedule;
  onToggle: () => void;
  onDelete: () => void;
  onEdit: () => void;
}) {
  const [isDeleting, setIsDeleting] = useState(false);

  const handleDelete = async () => {
    if (!confirm(`Delete schedule "${schedule.name}"?`)) {
      return;
    }

    setIsDeleting(true);
    try {
      await onDelete();
    } catch (error) {
      console.error('Delete failed:', error);
      alert(`Failed to delete schedule: ${error instanceof Error ? error.message : 'Unknown error'}`);
    } finally {
      setIsDeleting(false);
    }
  };

  return (
    <tr className="hover:bg-slate-50">
      <td className="px-4 py-3">
        <button
          onClick={onToggle}
          className={`inline-flex h-6 w-11 items-center rounded-full transition ${
            schedule.is_active ? 'bg-brand-600' : 'bg-slate-200'
          }`}
        >
          <span
            className={`inline-block h-4 w-4 rounded-full bg-white transition ${
              schedule.is_active ? 'translate-x-6' : 'translate-x-1'
            }`}
          />
        </button>
      </td>
      <td className="px-4 py-3">
        <div className="font-medium text-slate-900">{schedule.name}</div>
        {schedule.description && (
          <div className="text-sm text-slate-500">{schedule.description}</div>
        )}
      </td>
      <td className="px-4 py-3 text-sm text-slate-600">
        {cronToHuman(schedule.cron_expression)}
      </td>
      <td className="px-4 py-3 text-sm text-slate-600">
        {formatNextRun(schedule.next_run)}
      </td>
      <td className="px-4 py-3 text-sm text-slate-600">
        {schedule.target_type}
      </td>
      <td className="px-4 py-3 text-right">
        <div className="flex justify-end gap-2">
          <button
            onClick={onEdit}
            disabled={isDeleting}
            className="rounded-md border border-slate-200 px-3 py-1 text-sm font-medium text-slate-700 hover:bg-slate-50 disabled:opacity-50"
          >
            Edit
          </button>
          <button
            onClick={handleDelete}
            disabled={isDeleting}
            className="rounded-md border border-red-200 px-3 py-1 text-sm font-medium text-red-700 hover:bg-red-50 disabled:opacity-50"
          >
            {isDeleting ? 'Deleting...' : 'Delete'}
          </button>
        </div>
      </td>
    </tr>
  );
}
