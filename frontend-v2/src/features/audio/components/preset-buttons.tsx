import { Play } from 'lucide-react';
import { usePresets, useRecallPreset } from '../hooks/use-audio';

interface PresetButtonsProps {
  controllerId: string;
  controllerName: string;
}

export function PresetButtons({ controllerId, controllerName }: PresetButtonsProps) {
  const { data: presetData, isLoading } = usePresets(controllerId);
  const recallPreset = useRecallPreset();

  if (isLoading) {
    return (
      <div className="rounded-lg border border-slate-200 bg-white p-4">
        <p className="text-sm text-slate-500">Loading presets...</p>
      </div>
    );
  }

  if (!presetData || !presetData.presets || presetData.presets.length === 0) {
    return null; // Don't show presets section if no presets
  }

  const validPresets = presetData.presets.filter(p => p.is_valid);

  if (validPresets.length === 0) {
    return null; // Don't show if no valid presets
  }

  const handleRecall = (presetNumber: number) => {
    recallPreset.mutate({ controllerId, presetNumber });
  };

  // Clean preset name by removing null bytes and control characters
  const cleanPresetName = (name: string): string => {
    return name.replace(/\0/g, '').replace(/[\x00-\x1F\x7F]/g, '').trim();
  };

  return (
    <div className="rounded-lg border border-slate-200 bg-white p-4 shadow-sm">
      <h4 className="text-sm font-semibold text-slate-900 mb-3">
        Presets
      </h4>
      <div className="grid grid-cols-2 gap-2 sm:grid-cols-4 md:grid-cols-4">
        {validPresets.map((preset) => (
          <button
            key={preset.preset_number}
            onClick={() => handleRecall(preset.preset_number)}
            disabled={recallPreset.isPending}
            className="flex items-center gap-2 rounded-md border border-slate-300 bg-white px-3 py-2 text-sm font-medium text-slate-700 transition hover:bg-slate-50 hover:border-brand-400 disabled:cursor-not-allowed disabled:opacity-50"
            title={`Recall preset: ${cleanPresetName(preset.preset_name)}`}
          >
            <Play className="h-3.5 w-3.5 text-brand-500" />
            <span className="truncate">
              {cleanPresetName(preset.preset_name) || `Preset ${preset.preset_number}`}
            </span>
          </button>
        ))}
      </div>
    </div>
  );
}
