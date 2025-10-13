import { useMemo } from 'react';
import type { ChannelOption, DeviceTag } from '@/types';
import { formatRelativeTime } from '@/utils/datetime';
import { usePortStatus, getLastChannelForPort, getPowerStateForPort } from '@/features/devices/hooks/use-port-status';

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

interface PortRow {
  id: string;
  portId: number;
  controllerId: number;
  controllerName: string;
  hostname: string;
  portNumber: number;
  deviceName: string;
  location: string;
  tags: DeviceTag[];
  lastSeen: string;
  isOnline: boolean;
  defaultChannel: string | null;
}

interface GlassmorphicDeviceCardProps {
  row: PortRow;
  channels: ChannelOption[];
  selected: boolean;
  onToggle: () => void;
  onTagSelect: (tagId: number) => void;
  theme: Theme;
}

export const GlassmorphicDeviceCard = ({
  row,
  channels,
  selected,
  onToggle,
  onTagSelect,
  theme,
}: GlassmorphicDeviceCardProps) => {
  const { data: portStatus } = usePortStatus(row.hostname);
  const lastChannel = getLastChannelForPort(portStatus, row.portNumber);
  const powerState = getPowerStateForPort(portStatus, row.portNumber);

  const channelInfo = useMemo(() => {
    if (!lastChannel) return null;
    const channel = channels.find(
      (ch) => ch.lcn === lastChannel || ch.foxtel_number === lastChannel
    );
    if (!channel) return { lcn: lastChannel, name: null };
    const displayName = channel.channel_name.length > 12
      ? channel.channel_name.substring(0, 12) + '...'
      : channel.channel_name;
    return { lcn: lastChannel, name: displayName };
  }, [lastChannel, channels]);

  return (
    <button
      type="button"
      onClick={onToggle}
      className="group relative flex min-h-[160px] w-full flex-col justify-between overflow-hidden rounded-3xl p-6 text-left shadow-2xl backdrop-blur-xl transition-all duration-300 hover:scale-[1.02] active:scale-[0.98]"
      style={{
        backgroundColor: theme.colors.cardBg,
        border: selected
          ? `3px solid ${theme.colors.primary}`
          : `2px solid ${theme.colors.cardBorder}`,
        boxShadow: selected
          ? `0 0 30px ${theme.colors.primary}80, 0 20px 40px rgba(0,0,0,0.3)`
          : '0 20px 40px rgba(0,0,0,0.2)',
      }}
    >
      {/* Animated gradient overlay on hover */}
      <div
        className="absolute inset-0 opacity-0 transition-opacity duration-300 group-hover:opacity-10"
        style={{
          background: `linear-gradient(135deg, ${theme.colors.primary}, ${theme.colors.secondary}, ${theme.colors.accent})`,
        }}
      />

      {/* Header */}
      <div className="relative z-10">
        <div className="mb-3 flex items-start justify-between">
          <div className="flex items-center gap-3">
            {/* Power indicator - larger and glowing */}
            {powerState && (
              <div className="relative">
                <div
                  className={`h-4 w-4 rounded-full ${
                    powerState === 'on' ? 'animate-pulse' : ''
                  }`}
                  style={{
                    backgroundColor: powerState === 'on' ? theme.colors.success : theme.colors.danger,
                    boxShadow: powerState === 'on'
                      ? `0 0 15px ${theme.colors.success}, 0 0 30px ${theme.colors.success}50`
                      : `0 0 10px ${theme.colors.danger}50`,
                  }}
                />
              </div>
            )}
            <h3
              className="text-2xl font-bold leading-tight"
              style={{ color: theme.colors.textPrimary }}
            >
              {row.deviceName}
            </h3>
          </div>

          {/* Channel badge */}
          {channelInfo && (
            <div
              className="rounded-xl px-3 py-2 text-sm font-bold shadow-lg"
              style={{
                backgroundColor: theme.colors.primary,
                color: '#ffffff',
                boxShadow: `0 4px 15px ${theme.colors.primary}50`,
              }}
            >
              {channelInfo.name || `CH ${channelInfo.lcn}`}
            </div>
          )}
        </div>

        {/* Status info */}
        <div
          className="mb-4 flex flex-wrap items-center gap-2 text-sm"
          style={{ color: theme.colors.textSecondary }}
        >
          <span>Updated {formatRelativeTime(row.lastSeen)}</span>
          {!row.isOnline && (
            <>
              <span>•</span>
              <span className="font-semibold text-red-400">Controller Offline</span>
            </>
          )}
        </div>

        {/* Tags - horizontal scroll */}
        {row.tags.length > 0 && (
          <div className="mb-4 flex gap-2 overflow-x-auto pb-2" onClick={(e) => e.stopPropagation()}>
            {row.tags.map((tag) => (
              <button
                key={tag.id}
                type="button"
                onClick={(e) => {
                  e.stopPropagation();
                  onTagSelect(tag.id);
                }}
                className="min-h-[36px] flex-shrink-0 rounded-full px-4 py-1.5 text-sm font-bold transition-all hover:scale-105 active:scale-95"
                style={{
                  backgroundColor: tag.color ? `${tag.color}40` : 'rgba(255, 255, 255, 0.2)',
                  border: `2px solid ${tag.color || 'rgba(255, 255, 255, 0.4)'}`,
                  color: '#ffffff',
                  boxShadow: `0 4px 15px ${tag.color || 'rgba(0, 0, 0, 0.2)'}30`,
                }}
              >
                {tag.name}
              </button>
            ))}
          </div>
        )}
      </div>


      {/* Selected indicator */}
      {selected && (
        <div
          className="absolute right-4 top-4 z-20 rounded-full p-2"
          style={{
            backgroundColor: theme.colors.primary,
            boxShadow: `0 4px 20px ${theme.colors.primary}80`,
          }}
        >
          <svg className="h-6 w-6 text-white" fill="currentColor" viewBox="0 0 20 20">
            <path
              fillRule="evenodd"
              d="M16.707 5.293a1 1 0 010 1.414l-8 8a1 1 0 01-1.414 0l-4-4a1 1 0 011.414-1.414L8 12.586l7.293-7.293a1 1 0 011.414 0z"
              clipRule="evenodd"
            />
          </svg>
        </div>
      )}
    </button>
  );
};
