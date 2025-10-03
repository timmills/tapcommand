import { useAvailableChannels } from '@/features/devices/hooks/use-available-channels';
import type { ScheduleAction } from '../types/schedule';
import { ACTION_TYPE_LABELS, WAIT_TIME_OPTIONS, POWER_OPTIONS, MUTE_OPTIONS, VOLUME_REPEAT_OPTIONS } from '../types/schedule';

interface ActionBuilderProps {
  actions: ScheduleAction[];
  onChange: (actions: ScheduleAction[]) => void;
}

export function ActionBuilder({ actions, onChange }: ActionBuilderProps) {
  const { data: channels } = useAvailableChannels();

  const addAction = () => {
    if (actions.length >= 4) return;
    onChange([...actions, { type: 'power', wait_after: 0 }]);
  };

  const removeAction = (index: number) => {
    onChange(actions.filter((_, i) => i !== index));
  };

  const updateAction = (index: number, updates: Partial<ScheduleAction>) => {
    const newActions = [...actions];
    newActions[index] = { ...newActions[index], ...updates };
    onChange(newActions);
  };

  return (
    <div className="space-y-4">
      {/* Actions List */}
      {actions.map((action, index) => (
        <ActionRow
          key={index}
          index={index}
          action={action}
          channels={channels || []}
          onUpdate={(updates) => updateAction(index, updates)}
          onRemove={() => removeAction(index)}
          showWait={index < actions.length - 1}
        />
      ))}

      {/* Add Action Button */}
      {actions.length < 4 && (
        <button
          type="button"
          onClick={addAction}
          className="w-full py-2 px-4 border-2 border-dashed border-slate-300 rounded-md text-sm font-medium text-slate-600 hover:border-brand-400 hover:text-brand-600"
        >
          + Add Action
        </button>
      )}

      {actions.length >= 4 && (
        <div className="text-sm text-slate-500 text-center">
          Maximum of 4 actions reached
        </div>
      )}

      {/* Action Summary */}
      {actions.length > 0 && (
        <div className="rounded-md bg-slate-50 p-3">
          <div className="text-sm font-medium text-slate-700 mb-1">Action Sequence:</div>
          <div className="text-sm text-slate-600 space-y-1">
            {actions.map((action, index) => (
              <div key={index}>
                {index + 1}. {getActionSummary(action, channels || [])}
                {action.wait_after && action.wait_after > 0 ? ` → wait ${formatWaitTime(action.wait_after)}` : ''}
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}

interface ActionRowProps {
  index: number;
  action: ScheduleAction;
  channels: any[];
  onUpdate: (updates: Partial<ScheduleAction>) => void;
  onRemove: () => void;
  showWait: boolean;
}

function ActionRow({ index, action, channels, onUpdate, onRemove, showWait }: ActionRowProps) {
  return (
    <div className="border border-slate-200 rounded-md p-4 space-y-3">
      <div className="flex items-center justify-between">
        <div className="text-sm font-semibold text-slate-700">Action {index + 1}</div>
        <button
          type="button"
          onClick={onRemove}
          className="text-sm text-red-600 hover:text-red-700"
        >
          Remove
        </button>
      </div>

      {/* Action Type */}
      <div className="grid grid-cols-2 gap-3">
        <div>
          <label className="block text-xs font-medium text-slate-700 mb-1">Action Type</label>
          <select
            value={action.type}
            onChange={(e) => onUpdate({ type: e.target.value as ScheduleAction['type'], value: undefined, repeat: undefined })}
            className="block w-full text-sm rounded-md border-slate-300 shadow-sm focus:border-brand-500 focus:ring-brand-500"
          >
            {Object.entries(ACTION_TYPE_LABELS).map(([value, label]) => (
              <option key={value} value={value}>
                {label}
              </option>
            ))}
          </select>
        </div>

        {/* Action-specific inputs */}
        {action.type === 'power' && (
          <div>
            <label className="block text-xs font-medium text-slate-700 mb-1">Power State</label>
            <select
              value={action.value || 'toggle'}
              onChange={(e) => onUpdate({ value: e.target.value })}
              className="block w-full text-sm rounded-md border-slate-300 shadow-sm focus:border-brand-500 focus:ring-brand-500"
            >
              {POWER_OPTIONS.map((opt) => (
                <option key={opt.value} value={opt.value}>
                  {opt.label}
                </option>
              ))}
            </select>
          </div>
        )}

        {action.type === 'mute' && (
          <div>
            <label className="block text-xs font-medium text-slate-700 mb-1">Mute State</label>
            <select
              value={action.value || 'toggle'}
              onChange={(e) => onUpdate({ value: e.target.value })}
              className="block w-full text-sm rounded-md border-slate-300 shadow-sm focus:border-brand-500 focus:ring-brand-500"
            >
              {MUTE_OPTIONS.map((opt) => (
                <option key={opt.value} value={opt.value}>
                  {opt.label}
                </option>
              ))}
            </select>
          </div>
        )}

        {(action.type === 'volume_up' || action.type === 'volume_down') && (
          <div>
            <label className="block text-xs font-medium text-slate-700 mb-1">Repeat</label>
            <select
              value={action.repeat || 1}
              onChange={(e) => onUpdate({ repeat: parseInt(e.target.value) })}
              className="block w-full text-sm rounded-md border-slate-300 shadow-sm focus:border-brand-500 focus:ring-brand-500"
            >
              {VOLUME_REPEAT_OPTIONS.map((opt) => (
                <option key={opt.value} value={opt.value}>
                  {opt.label}
                </option>
              ))}
            </select>
          </div>
        )}

        {action.type === 'channel' && (
          <div>
            <label className="block text-xs font-medium text-slate-700 mb-1">Channel</label>
            <select
              value={action.value || ''}
              onChange={(e) => onUpdate({ value: e.target.value })}
              className="block w-full text-sm rounded-md border-slate-300 shadow-sm focus:border-brand-500 focus:ring-brand-500"
            >
              <option value="">Select channel...</option>
              {channels.map((ch) => (
                <option key={ch.id} value={ch.id.toString()}>
                  {ch.channel_name} ({ch.lcn || ch.foxtel_number})
                </option>
              ))}
            </select>
          </div>
        )}
      </div>

      {/* Wait After */}
      {showWait && (
        <div>
          <label className="block text-xs font-medium text-slate-700 mb-1">Wait After</label>
          <select
            value={action.wait_after || 0}
            onChange={(e) => onUpdate({ wait_after: parseInt(e.target.value) })}
            className="block w-full text-sm rounded-md border-slate-300 shadow-sm focus:border-brand-500 focus:ring-brand-500"
          >
            {WAIT_TIME_OPTIONS.map((opt) => (
              <option key={opt.value} value={opt.value}>
                {opt.label}
              </option>
            ))}
          </select>
        </div>
      )}
    </div>
  );
}

function getActionSummary(action: ScheduleAction, channels: any[]): string {
  switch (action.type) {
    case 'power':
      return `Power ${action.value || 'toggle'}`;
    case 'mute':
      return `Mute ${action.value || 'toggle'}`;
    case 'volume_up':
      return `Volume up ${action.repeat ? `x${action.repeat}` : ''}`;
    case 'volume_down':
      return `Volume down ${action.repeat ? `x${action.repeat}` : ''}`;
    case 'channel':
      const channel = channels.find((ch) => ch.id.toString() === action.value);
      return `Channel: ${channel ? channel.channel_name : action.value}`;
    case 'default_channel':
      return 'Default channel';
    default:
      return action.type;
  }
}

function formatWaitTime(seconds: number): string {
  if (seconds < 60) return `${seconds}s`;
  if (seconds < 3600) return `${seconds / 60}m`;
  return `${seconds / 3600}h`;
}
