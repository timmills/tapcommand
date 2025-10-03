import { useState, useEffect } from 'react';
import { useCreateSchedule, useUpdateSchedule } from '../hooks/use-schedules';
import { CronBuilder } from './cron-builder';
import { DeviceSelector } from './device-selector';
import { ActionBuilder } from './action-builder';
import type { Schedule, ScheduleAction } from '../types/schedule';

interface ScheduleFormModalProps {
  isOpen: boolean;
  onClose: () => void;
  schedule?: Schedule; // For editing
}

export function ScheduleFormModal({ isOpen, onClose, schedule }: ScheduleFormModalProps) {
  const createSchedule = useCreateSchedule();
  const updateSchedule = useUpdateSchedule();

  // Form state
  const [name, setName] = useState('');
  const [description, setDescription] = useState('');
  const [cronExpression, setCronExpression] = useState('0 8 * * 1-5');
  const [targetType, setTargetType] = useState('all');
  const [targetData, setTargetData] = useState<Record<string, any>>({});
  const [actions, setActions] = useState<ScheduleAction[]>([
    { type: 'power', wait_after: 0 },
  ]);
  const [isActive, setIsActive] = useState(true);

  // Load schedule data when editing
  useEffect(() => {
    if (schedule) {
      setName(schedule.name);
      setDescription(schedule.description || '');
      setCronExpression(schedule.cron_expression);
      setTargetType(schedule.target_type);
      setTargetData(schedule.target_data || {});
      setActions(schedule.actions);
      setIsActive(schedule.is_active);
    } else {
      // Reset form for new schedule
      setName('');
      setDescription('');
      setCronExpression('0 8 * * 1-5');
      setTargetType('all');
      setTargetData({});
      setActions([{ type: 'power', wait_after: 0 }]);
      setIsActive(true);
    }
  }, [schedule]);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();

    const data = {
      name,
      description: description || undefined,
      cron_expression: cronExpression,
      target_type: targetType,
      target_data: targetType === 'all' ? undefined : targetData,
      actions,
      is_active: isActive,
    };

    try {
      if (schedule) {
        await updateSchedule.mutateAsync({ id: schedule.id, data });
      } else {
        await createSchedule.mutateAsync(data);
      }
      onClose();
    } catch (error) {
      console.error('Failed to save schedule:', error);
      alert(`Failed to save schedule: ${(error as Error).message}`);
    }
  };

  if (!isOpen) return null;

  return (
    <div className="fixed inset-0 z-50 overflow-y-auto">
      <div className="flex min-h-screen items-center justify-center p-4">
        {/* Backdrop */}
        <div className="fixed inset-0 bg-black bg-opacity-25" onClick={onClose} />

        {/* Modal */}
        <div className="relative w-full max-w-2xl rounded-lg bg-white shadow-xl">
          {/* Header */}
          <div className="flex items-center justify-between border-b border-slate-200 px-6 py-4">
            <h2 className="text-xl font-semibold text-slate-900">
              {schedule ? 'Edit Schedule' : 'Create Schedule'}
            </h2>
            <button
              onClick={onClose}
              className="text-slate-400 hover:text-slate-500"
            >
              <svg className="h-6 w-6" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
              </svg>
            </button>
          </div>

          {/* Form */}
          <form onSubmit={handleSubmit} className="px-6 py-4">
            <div className="space-y-6">
              {/* Basic Info */}
              <div className="space-y-4">
                <h3 className="text-lg font-medium text-slate-900">Basic Information</h3>

                <div>
                  <label className="block text-sm font-medium text-slate-700 mb-1">
                    Schedule Name <span className="text-red-500">*</span>
                  </label>
                  <input
                    type="text"
                    value={name}
                    onChange={(e) => setName(e.target.value)}
                    required
                    placeholder="e.g., Morning Bar Setup"
                    className="block w-full rounded-md border-slate-300 shadow-sm focus:border-brand-500 focus:ring-brand-500"
                  />
                </div>

                <div>
                  <label className="block text-sm font-medium text-slate-700 mb-1">
                    Description (optional)
                  </label>
                  <textarea
                    value={description}
                    onChange={(e) => setDescription(e.target.value)}
                    rows={2}
                    placeholder="Describe what this schedule does..."
                    className="block w-full rounded-md border-slate-300 shadow-sm focus:border-brand-500 focus:ring-brand-500"
                  />
                </div>
              </div>

              {/* Timing */}
              <div className="space-y-4">
                <h3 className="text-lg font-medium text-slate-900">When to Run</h3>
                <CronBuilder value={cronExpression} onChange={setCronExpression} />
              </div>

              {/* Targets */}
              <div className="space-y-4">
                <h3 className="text-lg font-medium text-slate-900">Target Devices</h3>
                <DeviceSelector
                  targetType={targetType}
                  targetData={targetData}
                  onChange={(type, data) => {
                    setTargetType(type);
                    setTargetData(data);
                  }}
                />
              </div>

              {/* Actions */}
              <div className="space-y-4">
                <h3 className="text-lg font-medium text-slate-900">Actions</h3>
                <ActionBuilder actions={actions} onChange={setActions} />
              </div>

              {/* Active Toggle */}
              <div className="flex items-center gap-3">
                <label className="flex items-center gap-2">
                  <input
                    type="checkbox"
                    checked={isActive}
                    onChange={(e) => setIsActive(e.target.checked)}
                    className="h-4 w-4 rounded border-slate-300 text-brand-600 focus:ring-brand-500"
                  />
                  <span className="text-sm font-medium text-slate-700">
                    Active (schedule will run automatically)
                  </span>
                </label>
              </div>
            </div>

            {/* Footer */}
            <div className="mt-6 flex justify-end gap-3 border-t border-slate-200 pt-4">
              <button
                type="button"
                onClick={onClose}
                className="px-4 py-2 text-sm font-medium text-slate-700 hover:text-slate-800"
              >
                Cancel
              </button>
              <button
                type="submit"
                disabled={createSchedule.isPending || updateSchedule.isPending}
                className="rounded-md bg-brand-600 px-4 py-2 text-sm font-semibold text-white shadow-sm hover:bg-brand-700 disabled:opacity-50"
              >
                {createSchedule.isPending || updateSchedule.isPending
                  ? 'Saving...'
                  : schedule
                    ? 'Update Schedule'
                    : 'Create Schedule'}
              </button>
            </div>
          </form>
        </div>
      </div>
    </div>
  );
}
