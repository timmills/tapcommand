import { useState, useMemo, useEffect } from 'react';
import { Volume2, VolumeX, Play, ChevronUp, ChevronDown, RefreshCw, Download } from 'lucide-react';
import { useAudioControllers, useSetVolume, useToggleMute, useRecallPreset, useSetMasterVolume, useMasterVolumeUp, useMasterVolumeDown, useSyncVolumes, useActivePreset } from '../hooks/use-audio';
import { ThemeSelector } from '@/features/control/components/theme-selector';
import type { AudioController, AudioZone } from '../api/audio-api';

type Theme = {
  id: string;
  name: string;
  description: string;
  colors: {
    gradientFrom: string;
    gradientVia?: string;
    gradientTo: string;
    cardBg: string;
    cardBorder: string;
    cardBorderHover: string;
    primary: string;
    primaryHover: string;
    secondary: string;
    accent: string;
    textPrimary: string;
    textSecondary: string;
    success: string;
    danger: string;
    warning: string;
  };
};

const themes: Theme[] = [
  {
    id: 'neon-club',
    name: 'Neon Club',
    description: 'Vibrant pink and purple for high-energy venues',
    colors: {
      gradientFrom: '#667eea',
      gradientVia: '#764ba2',
      gradientTo: '#f093fb',
      cardBg: 'rgba(255, 255, 255, 0.1)',
      cardBorder: 'rgba(255, 255, 255, 0.2)',
      cardBorderHover: '#FF006E',
      primary: '#FF006E',
      primaryHover: '#D4005E',
      secondary: '#8338EC',
      accent: '#00F5FF',
      textPrimary: '#ffffff',
      textSecondary: 'rgba(255, 255, 255, 0.7)',
      success: '#10B981',
      danger: '#EF4444',
      warning: '#F59E0B',
    },
  },
  {
    id: 'sports-bar',
    name: 'Sports Bar',
    description: 'Electric blue and orange for sports venues',
    colors: {
      gradientFrom: '#1e3a8a',
      gradientVia: '#3b82f6',
      gradientTo: '#60a5fa',
      cardBg: 'rgba(255, 255, 255, 0.1)',
      cardBorder: 'rgba(255, 255, 255, 0.2)',
      cardBorderHover: '#00D9FF',
      primary: '#00D9FF',
      primaryHover: '#00B8D4',
      secondary: '#F97316',
      accent: '#10B981',
      textPrimary: '#ffffff',
      textSecondary: 'rgba(255, 255, 255, 0.7)',
      success: '#10B981',
      danger: '#EF4444',
      warning: '#F59E0B',
    },
  },
  {
    id: 'premium-lounge',
    name: 'Premium Lounge',
    description: 'Sophisticated gold and deep slate',
    colors: {
      gradientFrom: '#0f172a',
      gradientVia: '#1e293b',
      gradientTo: '#334155',
      cardBg: 'rgba(255, 255, 255, 0.08)',
      cardBorder: 'rgba(255, 255, 255, 0.15)',
      cardBorderHover: '#FFD700',
      primary: '#FFD700',
      primaryHover: '#FFC700',
      secondary: '#06b6d4',
      accent: '#8b5cf6',
      textPrimary: '#ffffff',
      textSecondary: 'rgba(255, 255, 255, 0.6)',
      success: '#10B981',
      danger: '#EF4444',
      warning: '#F59E0B',
    },
  },
  {
    id: 'sunset-lounge',
    name: 'Sunset Lounge',
    description: 'Warm sunset colors for relaxed atmosphere',
    colors: {
      gradientFrom: '#ec4899',
      gradientVia: '#f97316',
      gradientTo: '#fbbf24',
      cardBg: 'rgba(255, 255, 255, 0.12)',
      cardBorder: 'rgba(255, 255, 255, 0.2)',
      cardBorderHover: '#fbbf24',
      primary: '#fbbf24',
      primaryHover: '#f59e0b',
      secondary: '#ec4899',
      accent: '#f97316',
      textPrimary: '#ffffff',
      textSecondary: 'rgba(255, 255, 255, 0.8)',
      success: '#10B981',
      danger: '#EF4444',
      warning: '#F59E0B',
    },
  },
  {
    id: 'ocean-breeze',
    name: 'Ocean Breeze',
    description: 'Cool teal and cyan for coastal venues',
    colors: {
      gradientFrom: '#0e7490',
      gradientVia: '#06b6d4',
      gradientTo: '#22d3ee',
      cardBg: 'rgba(255, 255, 255, 0.1)',
      cardBorder: 'rgba(255, 255, 255, 0.2)',
      cardBorderHover: '#22d3ee',
      primary: '#22d3ee',
      primaryHover: '#06b6d4',
      secondary: '#3b82f6',
      accent: '#8b5cf6',
      textPrimary: '#ffffff',
      textSecondary: 'rgba(255, 255, 255, 0.7)',
      success: '#10B981',
      danger: '#EF4444',
      warning: '#F59E0B',
    },
  },
];

interface MasterControlBarProps {
  controller: AudioController;
  theme: Theme;
}

function MasterControlBar({ controller, theme }: MasterControlBarProps) {
  const recallPreset = useRecallPreset();

  const presets = controller.connection_config?.presets || [];
  const validPresets = presets.filter(p => p.is_valid);
  const isOnline = controller.is_online;

  return (
    <div className="space-y-4">
      {/* Presets */}
      {validPresets.length > 0 && (
        <div>
          <h4
            className="mb-2 text-xs font-bold uppercase tracking-wider"
            style={{ color: theme.colors.textSecondary }}
          >
            Quick Presets
          </h4>
          <div className="grid grid-cols-4 gap-2">
            {validPresets.map((preset) => (
              <button
                key={preset.preset_number}
                onClick={() => recallPreset.mutate({ controllerId: controller.controller_id, presetNumber: preset.preset_number })}
                disabled={!isOnline || recallPreset.isPending}
                className="flex items-center justify-center gap-2 rounded-xl py-2 text-sm font-bold transition-all hover:scale-105 active:scale-95 disabled:cursor-not-allowed disabled:opacity-50"
                style={{
                  backgroundColor: `${theme.colors.secondary}30`,
                  border: `2px solid ${theme.colors.secondary}`,
                  color: theme.colors.textPrimary,
                }}
                title={preset.preset_name.replace(/\0/g, '').replace(/[\x00-\x1F\x7F]/g, '').trim()}
              >
                <Play className="h-3 w-3" />
                <span className="truncate">
                  {preset.preset_name.replace(/\0/g, '').replace(/[\x00-\x1F\x7F]/g, '').trim()}
                </span>
              </button>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}

interface ZoneCardProps {
  zone: AudioZone;
  theme: Theme;
}

function AudioZoneCard({ zone, theme }: ZoneCardProps) {
  const [localVolume, setLocalVolume] = useState(zone.volume_level ?? 50);
  const setVolume = useSetVolume();
  const toggleMute = useToggleMute();

  const volume = zone.volume_level ?? 50;
  const isMuted = zone.is_muted ?? false;
  const isOnline = zone.is_online;

  // Update local volume when server value changes (but not while user is dragging)
  useEffect(() => {
    if (!setVolume.isPending) {
      setLocalVolume(volume);
    }
  }, [volume, setVolume.isPending]);

  const handleVolumeChange = (newVolume: number) => {
    setLocalVolume(newVolume);
  };

  const handleVolumeCommit = () => {
    if (localVolume !== volume) {
      setVolume.mutate({ zoneId: zone.id, volume: localVolume });
    }
  };

  return (
    <div
      className="rounded-3xl p-6 backdrop-blur-xl transition-all hover:scale-[1.02]"
      style={{
        backgroundColor: theme.colors.cardBg,
        border: `2px solid ${theme.colors.cardBorder}`,
      }}
    >
      {/* Zone Header */}
      <div className="mb-4 flex items-start justify-between">
        <div>
          <h3
            className="text-2xl font-black"
            style={{ color: theme.colors.textPrimary }}
          >
            {zone.zone_name}
          </h3>
          <p
            className="text-sm font-medium"
            style={{ color: theme.colors.textSecondary }}
          >
            Zone {zone.zone_number}
          </p>
        </div>
        <div
          className={`rounded-full px-3 py-1 text-xs font-bold ${
            isOnline ? 'animate-pulse' : ''
          }`}
          style={{
            backgroundColor: isOnline ? `${theme.colors.success}40` : `${theme.colors.danger}40`,
            border: `2px solid ${isOnline ? theme.colors.success : theme.colors.danger}`,
            color: theme.colors.textPrimary,
          }}
        >
          {isOnline ? '● ONLINE' : '○ OFFLINE'}
        </div>
      </div>

      {/* Mute Button */}
      <button
        onClick={() => toggleMute.mutate(zone.id)}
        disabled={!isOnline || toggleMute.isPending}
        className="mb-4 w-full rounded-2xl py-3 font-bold transition-all hover:scale-105 active:scale-95 disabled:cursor-not-allowed disabled:opacity-50"
        style={{
          backgroundColor: isMuted ? `${theme.colors.danger}60` : `${theme.colors.secondary}30`,
          border: `2px solid ${isMuted ? theme.colors.danger : theme.colors.secondary}`,
          color: theme.colors.textPrimary,
          boxShadow: `0 4px 15px ${isMuted ? theme.colors.danger : theme.colors.secondary}30`,
        }}
      >
        <div className="flex items-center justify-center gap-2">
          {isMuted ? <VolumeX className="h-5 w-5" /> : <Volume2 className="h-5 w-5" />}
          <span className="text-lg">
            {isMuted ? 'MUTED' : 'UNMUTED'}
          </span>
        </div>
      </button>

      {/* Volume Control */}
      <div className="space-y-3">
        <div className="flex items-center justify-between">
          <span
            className="text-sm font-bold uppercase tracking-wider"
            style={{ color: theme.colors.textSecondary }}
          >
            Volume
          </span>
          <span
            className="text-3xl font-black"
            style={{ color: theme.colors.textPrimary }}
          >
            {volume}%
          </span>
        </div>
        <div className="grid grid-cols-5 gap-2">
          {(() => {
            const volumeOptions = [10, 20, 30, 40, 50, 60, 70, 80, 90, 100];
            const closestVolume = volumeOptions.reduce((prev, curr) =>
              Math.abs(curr - volume) < Math.abs(prev - volume) ? curr : prev
            );
            return volumeOptions.map((vol) => (
              <button
                key={vol}
                onClick={() => setVolume.mutate({ zoneId: zone.id, volume: vol })}
                disabled={!isOnline || isMuted || setVolume.isPending}
                className="rounded-lg py-2 text-sm font-bold transition-all hover:scale-105 active:scale-95 disabled:cursor-not-allowed disabled:opacity-50"
                style={{
                  backgroundColor: vol === closestVolume ? `${theme.colors.primary}` : `${theme.colors.primary}30`,
                  border: `2px solid ${theme.colors.primary}`,
                  color: theme.colors.textPrimary,
                  boxShadow: vol === closestVolume ? `0 0 15px ${theme.colors.primary}80` : 'none',
                }}
              >
                {vol}%
              </button>
            ));
          })()}
        </div>
      </div>
    </div>
  );
}

interface ControllerCardProps {
  controller: AudioController;
  theme: Theme;
  onSyncVolumes: (controllerId: string) => void;
  onRefresh: () => void;
  isRefreshing: boolean;
  syncVolumesPending: boolean;
}

function ControllerCard({ controller, theme, onSyncVolumes, onRefresh, isRefreshing, syncVolumesPending }: ControllerCardProps) {
  const recallPreset = useRecallPreset();
  const presets = controller.connection_config?.presets || [];

  // Fetch active preset for Plena Matrix controllers
  const isPlenaMatrix = controller.connection_config?.device_model === 'PLM-4P125' ||
    controller.connection_config?.device_model === 'PLM-4P220' ||
    controller.connection_config?.device_model === 'PLM-4P120';

  const { data: activePresetData } = useActivePreset(
    controller.controller_id,
    isPlenaMatrix && controller.is_online
  );

  return (
    <div
      className="mb-6 overflow-hidden rounded-3xl backdrop-blur-xl"
      style={{
        backgroundColor: theme.colors.cardBg,
        border: `2px solid ${theme.colors.cardBorder}`,
      }}
    >
      {/* Controller Header */}
      <div className="p-6 space-y-4">
        <div className="flex items-start justify-between">
          <div>
            <h2
              className="text-3xl font-black"
              style={{ color: theme.colors.textPrimary }}
            >
              {controller.controller_name}
            </h2>
            <p
              className="mt-1 text-lg font-medium"
              style={{ color: theme.colors.textSecondary }}
            >
              {controller.zones.length} zone{controller.zones.length === 1 ? '' : 's'} •{' '}
              {controller.zones.filter(z => z.is_online).length} online
            </p>
          </div>
          <div className="flex gap-2">
            {/* Sync volumes button - Only for Plena Matrix */}
            {isPlenaMatrix && (
              <button
                onClick={() => onSyncVolumes(controller.controller_id)}
                disabled={!controller.is_online || syncVolumesPending}
                className="rounded-full p-2 font-bold transition-all hover:scale-110 active:scale-95 disabled:cursor-not-allowed disabled:opacity-50"
                style={{
                  backgroundColor: `${theme.colors.secondary}30`,
                  border: `2px solid ${theme.colors.secondary}`,
                  color: theme.colors.textPrimary,
                }}
                title="Sync Volumes from Device"
              >
                <Download className={`h-5 w-5 ${syncVolumesPending ? 'animate-bounce' : ''}`} />
              </button>
            )}
            {/* Refresh button */}
            <button
              onClick={onRefresh}
              disabled={isRefreshing}
              className="rounded-full p-2 font-bold transition-all hover:scale-110 active:scale-95 disabled:cursor-not-allowed disabled:opacity-50"
              style={{
                backgroundColor: `${theme.colors.primary}30`,
                border: `2px solid ${theme.colors.primary}`,
                color: theme.colors.textPrimary,
              }}
              title="Refresh Controller Status"
            >
              <RefreshCw className={`h-5 w-5 ${isRefreshing ? 'animate-spin' : ''}`} />
            </button>
          </div>
        </div>

        {/* Master Controls - Only for non-Plena Matrix controllers */}
        {!isPlenaMatrix && (
          <MasterControlBar controller={controller} theme={theme} />
        )}

        {/* Presets - For Plena Matrix controllers */}
        {isPlenaMatrix && presets.length > 0 && (
          <div className="mt-4">
            <h4
              className="mb-2 text-xs font-bold uppercase tracking-wider"
              style={{ color: theme.colors.textSecondary }}
            >
              Quick Presets
            </h4>
            <div className="grid grid-cols-5 gap-2">
              {presets.filter(p => p.is_valid).map((preset) => {
                const isActive = activePresetData?.preset_number === preset.preset_number;
                return (
                  <button
                    key={preset.preset_number}
                    onClick={() => recallPreset.mutate({ controllerId: controller.controller_id, presetNumber: preset.preset_number })}
                    disabled={!controller.is_online || recallPreset.isPending}
                    className="flex items-center justify-center gap-2 rounded-xl py-2 text-sm font-bold transition-all hover:scale-105 active:scale-95 disabled:cursor-not-allowed disabled:opacity-50"
                    style={{
                      backgroundColor: isActive ? `${theme.colors.accent}60` : `${theme.colors.secondary}30`,
                      border: `3px solid ${isActive ? theme.colors.accent : theme.colors.secondary}`,
                      color: theme.colors.textPrimary,
                      boxShadow: isActive ? `0 0 20px ${theme.colors.accent}80` : 'none',
                    }}
                    title={preset.preset_name.replace(/\0/g, '').replace(/[\x00-\x1F\x7F]/g, '').trim()}
                  >
                    <Play className="h-3 w-3" />
                    <span className="truncate">
                      {preset.preset_name.replace(/\0/g, '').replace(/[\x00-\x1F\x7F]/g, '').trim()}
                    </span>
                  </button>
                );
              })}
            </div>
          </div>
        )}
      </div>

      {/* Zones Grid */}
      <div className="border-t p-6" style={{ borderColor: theme.colors.cardBorder }}>
        {controller.zones.length > 0 ? (
          <div className="grid gap-6 md:grid-cols-2 xl:grid-cols-3 2xl:grid-cols-4">
            {controller.zones.map((zone) => (
              <AudioZoneCard
                key={zone.id}
                zone={zone}
                theme={theme}
              />
            ))}
          </div>
        ) : (
          <div className="text-center" style={{ color: theme.colors.textSecondary }}>
            No zones configured
          </div>
        )}
      </div>
    </div>
  );
}

export function AudioControlDemoPage() {
  const { data: controllers = [], isLoading, refetch } = useAudioControllers(30000); // Poll every 30 seconds
  const [currentTheme, setCurrentTheme] = useState<Theme>(themes[0]);
  const [isRefreshing, setIsRefreshing] = useState(false);
  const syncVolumes = useSyncVolumes();

  const handleRefresh = async () => {
    setIsRefreshing(true);

    // For Plena Matrix controllers, sync volumes from device first
    const plenaControllers = controllers.filter(c =>
      c.connection_config?.device_model === 'PLM-4P125' ||
      c.connection_config?.device_model === 'PLM-4P220' ||
      c.connection_config?.device_model === 'PLM-4P120'
    );

    // Sync all Plena Matrix controllers in parallel
    if (plenaControllers.length > 0) {
      await Promise.allSettled(
        plenaControllers.map(c => syncVolumes.mutateAsync(c.controller_id))
      );
    }

    await refetch();
    setIsRefreshing(false);
  };

  const handleSyncVolumes = async (controllerId: string) => {
    syncVolumes.mutate(controllerId);
  };

  const controllersByLocation = useMemo(() => {
    const groups = new Map<string, AudioController[]>();
    controllers.forEach((controller) => {
      const location = controller.controller_name || 'Main Area';
      if (!groups.has(location)) {
        groups.set(location, []);
      }
      groups.get(location)!.push(controller);
    });
    return groups;
  }, [controllers]);

  return (
    <div
      className="min-h-screen transition-all duration-700"
      style={{
        background: `linear-gradient(135deg, ${currentTheme.colors.gradientFrom}, ${currentTheme.colors.gradientVia || currentTheme.colors.gradientTo}, ${currentTheme.colors.gradientTo})`,
      }}
    >
      {/* Theme Selector */}
      <ThemeSelector currentTheme={currentTheme} onThemeChange={setCurrentTheme} />

      {/* Main Content */}
      <div className="mx-auto max-w-[1600px] px-6 py-6">
        {/* Header */}
        <div className="mb-8 text-center">
          <h1
            className="mb-2 text-5xl font-black tracking-tight"
            style={{ color: currentTheme.colors.textPrimary }}
          >
            Audio Control
          </h1>
          <p
            className="text-xl font-medium"
            style={{ color: currentTheme.colors.textSecondary }}
          >
            {currentTheme.description}
          </p>
        </div>

        {/* Controllers */}
        {isLoading ? (
          <div
            className="rounded-3xl p-12 text-center backdrop-blur-xl"
            style={{
              backgroundColor: currentTheme.colors.cardBg,
              border: `2px solid ${currentTheme.colors.cardBorder}`,
              color: currentTheme.colors.textPrimary,
            }}
          >
            <div className="text-2xl font-bold">Loading audio zones...</div>
          </div>
        ) : controllers.length === 0 ? (
          <div
            className="rounded-3xl p-12 text-center backdrop-blur-xl"
            style={{
              backgroundColor: currentTheme.colors.cardBg,
              border: `2px solid ${currentTheme.colors.cardBorder}`,
              color: currentTheme.colors.textPrimary,
            }}
          >
            <div className="text-2xl font-bold">No audio controllers found</div>
            <p className="mt-2" style={{ color: currentTheme.colors.textSecondary }}>
              Please configure audio controllers in the Audio page
            </p>
          </div>
        ) : (
          <div className="space-y-6">
            {Array.from(controllersByLocation.entries()).map(([location, locationControllers]) => (
              <div key={location}>
                {locationControllers.map((controller) => (
                  <ControllerCard
                    key={controller.id}
                    controller={controller}
                    theme={currentTheme}
                    onSyncVolumes={handleSyncVolumes}
                    onRefresh={handleRefresh}
                    isRefreshing={isRefreshing}
                    syncVolumesPending={syncVolumes.isPending}
                  />
                ))}
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  );
}
