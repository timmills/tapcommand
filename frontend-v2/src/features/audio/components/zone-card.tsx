import { useState } from 'react';
import { Volume2, VolumeX, Volume1, Minus, Plus } from 'lucide-react';
import type { AudioZone } from '../api/audio-api';
import { useSetVolume, useVolumeUp, useVolumeDown, useToggleMute } from '../hooks/use-audio';

interface ZoneCardProps {
  zone: AudioZone;
}

export function ZoneCard({ zone }: ZoneCardProps) {
  const [localVolume, setLocalVolume] = useState(zone.volume_level ?? 50);
  const setVolume = useSetVolume();
  const volumeUp = useVolumeUp();
  const volumeDown = useVolumeDown();
  const toggleMute = useToggleMute();

  const volume = zone.volume_level ?? 50;
  const isMuted = zone.is_muted ?? false;
  const isOnline = zone.is_online;

  // Handle slider change (optimistic update)
  const handleVolumeChange = (newVolume: number) => {
    setLocalVolume(newVolume);
  };

  // Commit volume change when slider is released
  const handleVolumeCommit = () => {
    if (localVolume !== volume) {
      setVolume.mutate({ zoneId: zone.id, volume: localVolume });
    }
  };

  // Sync local volume when zone updates
  if (localVolume !== volume && !setVolume.isPending) {
    setLocalVolume(volume);
  }

  return (
    <div
      className={`rounded-lg border p-4 transition ${
        isOnline
          ? 'border-slate-200 bg-white'
          : 'border-slate-200 bg-slate-50 opacity-60'
      }`}
    >
      {/* Zone name and status */}
      <div className="mb-3 flex items-start justify-between">
        <div>
          <h3 className="font-medium text-slate-900">{zone.zone_name}</h3>
          <p className="text-xs text-slate-500">
            Zone {zone.zone_number} • {zone.protocol}
          </p>
        </div>
        <div
          className={`rounded-full px-2 py-0.5 text-xs font-medium ${
            isOnline
              ? 'bg-emerald-50 text-emerald-700'
              : 'bg-slate-100 text-slate-600'
          }`}
        >
          {isOnline ? 'Online' : 'Offline'}
        </div>
      </div>

      {/* Mute button */}
      {zone.has_mute && (
        <button
          onClick={() => toggleMute.mutate(zone.id)}
          disabled={!isOnline || toggleMute.isPending}
          className={`mb-3 w-full rounded-md p-2 transition ${
            isMuted
              ? 'bg-red-500 text-white hover:bg-red-600'
              : 'bg-slate-100 text-slate-700 hover:bg-slate-200'
          } disabled:cursor-not-allowed disabled:opacity-50`}
        >
          <div className="flex items-center justify-center gap-2">
            {isMuted ? <VolumeX className="h-4 w-4" /> : <Volume2 className="h-4 w-4" />}
            <span className="text-sm font-medium">
              {isMuted ? 'Muted' : 'Unmuted'}
            </span>
          </div>
        </button>
      )}

      {/* Volume controls */}
      <div className="space-y-2">
        {/* Volume slider */}
        <div className="flex items-center gap-3">
          <Volume1 className="h-4 w-4 flex-shrink-0 text-slate-400" />
          <input
            type="range"
            min="0"
            max="100"
            value={localVolume}
            onChange={(e) => handleVolumeChange(Number(e.target.value))}
            onMouseUp={handleVolumeCommit}
            onTouchEnd={handleVolumeCommit}
            disabled={!isOnline || isMuted}
            className="flex-1 accent-brand-500 disabled:cursor-not-allowed disabled:opacity-50"
          />
          <span className="w-12 text-right text-sm font-medium text-slate-700">
            {localVolume}%
          </span>
        </div>

        {/* Volume buttons */}
        <div className="flex gap-2">
          <button
            onClick={() => volumeDown.mutate(zone.id)}
            disabled={!isOnline || isMuted || volumeDown.isPending}
            className="flex flex-1 items-center justify-center gap-1 rounded-md border border-slate-300 px-3 py-1.5 text-sm font-medium text-slate-700 transition hover:bg-slate-50 disabled:cursor-not-allowed disabled:opacity-50"
          >
            <Minus className="h-3 w-3" />
            -5%
          </button>
          <button
            onClick={() => volumeUp.mutate(zone.id)}
            disabled={!isOnline || isMuted || volumeUp.isPending}
            className="flex flex-1 items-center justify-center gap-1 rounded-md border border-slate-300 px-3 py-1.5 text-sm font-medium text-slate-700 transition hover:bg-slate-50 disabled:cursor-not-allowed disabled:opacity-50"
          >
            <Plus className="h-3 w-3" />
            +5%
          </button>
        </div>
      </div>

      {/* Gain range indicator (if available) */}
      {zone.gain_range && (
        <div className="mt-2 text-xs text-slate-400">
          Range: {zone.gain_range[0]}dB to {zone.gain_range[1]}dB
        </div>
      )}
    </div>
  );
}
