# Control Demo Page - Implementation Guide

This document provides step-by-step instructions to recreate the glassmorphism-styled control demo page from scratch.

## Overview

The control-demo page is a vibrant, tablet-optimized interface with:
- 5 switchable glassmorphism themes
- Large touch-friendly controls (56px minimum)
- Enhanced device cards with status indicators
- Floating action toolbar for bulk operations
- Theme-aware color system

## File Structure

```
frontend-v2/src/features/control/
├── components/
│   ├── glassmorphic-device-card.tsx    # Enhanced device card component
│   ├── glassmorphic-action-toolbar.tsx # Floating action panel
│   └── theme-selector.tsx              # Theme picker UI
├── pages/
│   ├── control-demo-page.tsx           # Main demo page
│   └── control-demo-layout.tsx         # Auth wrapper layout
└── (Note: NO types/ directory needed - types are inlined)
```

## Step-by-Step Implementation

### Step 1: Create Theme Selector Component

**File**: `src/features/control/components/theme-selector.tsx`

<details>
<summary>Full code (click to expand)</summary>

```typescript
import { useState } from 'react';

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

interface ThemeSelectorProps {
  currentTheme: Theme;
  onThemeChange: (theme: Theme) => void;
}

export const ThemeSelector = ({ currentTheme, onThemeChange }: ThemeSelectorProps) => {
  const [isOpen, setIsOpen] = useState(false);

  return (
    <div className="fixed left-6 top-6 z-30">
      {/* Theme Button */}
      <button
        onClick={() => setIsOpen(!isOpen)}
        className="flex items-center gap-2 rounded-2xl px-4 py-3 text-sm font-semibold shadow-2xl backdrop-blur-xl transition-all hover:scale-105 active:scale-95"
        style={{
          backgroundColor: currentTheme.colors.cardBg,
          border: `2px solid ${currentTheme.colors.cardBorder}`,
          color: currentTheme.colors.textPrimary,
        }}
      >
        <svg className="h-5 w-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
          <path
            strokeLinecap="round"
            strokeLinejoin="round"
            strokeWidth={2}
            d="M7 21a4 4 0 01-4-4V5a2 2 0 012-2h4a2 2 0 012 2v12a4 4 0 01-4 4zm0 0h12a2 2 0 002-2v-4a2 2 0 00-2-2h-2.343M11 7.343l1.657-1.657a2 2 0 012.828 0l2.829 2.829a2 2 0 010 2.828l-8.486 8.485M7 17h.01"
          />
        </svg>
        {currentTheme.name}
      </button>

      {/* Theme Picker Panel */}
      {isOpen && (
        <div
          className="mt-3 w-80 rounded-2xl p-4 shadow-2xl backdrop-blur-xl"
          style={{
            backgroundColor: currentTheme.colors.cardBg,
            border: `2px solid ${currentTheme.colors.cardBorder}`,
          }}
        >
          <div className="mb-3 flex items-center justify-between">
            <h3
              className="text-lg font-bold"
              style={{ color: currentTheme.colors.textPrimary }}
            >
              Choose Theme
            </h3>
            <button
              onClick={() => setIsOpen(false)}
              className="rounded-lg p-1 transition-all hover:bg-white/10"
              style={{ color: currentTheme.colors.textSecondary }}
            >
              <svg className="h-5 w-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
              </svg>
            </button>
          </div>

          <div className="space-y-2">
            {themes.map((theme) => {
              const isActive = theme.id === currentTheme.id;
              return (
                <button
                  key={theme.id}
                  onClick={() => {
                    onThemeChange(theme);
                    setIsOpen(false);
                  }}
                  className="group w-full rounded-xl p-3 text-left transition-all hover:scale-[1.02] active:scale-[0.98]"
                  style={{
                    background: `linear-gradient(135deg, ${theme.colors.gradientFrom}, ${theme.colors.gradientVia || theme.colors.gradientTo}, ${theme.colors.gradientTo})`,
                    border: isActive ? `3px solid ${theme.colors.primary}` : '2px solid rgba(255, 255, 255, 0.2)',
                    boxShadow: isActive ? `0 0 20px ${theme.colors.primary}50` : 'none',
                  }}
                >
                  <div className="flex items-center justify-between">
                    <div>
                      <div className="font-bold text-white">{theme.name}</div>
                      <div className="text-xs text-white/80">{theme.description}</div>
                    </div>
                    {isActive && (
                      <svg
                        className="h-6 w-6 text-white"
                        fill="currentColor"
                        viewBox="0 0 20 20"
                      >
                        <path
                          fillRule="evenodd"
                          d="M10 18a8 8 0 100-16 8 8 0 000 16zm3.707-9.293a1 1 0 00-1.414-1.414L9 10.586 7.707 9.293a1 1 0 00-1.414 1.414l2 2a1 1 0 001.414 0l4-4z"
                          clipRule="evenodd"
                        />
                      </svg>
                    )}
                  </div>

                  {/* Color Palette Preview */}
                  <div className="mt-2 flex gap-1">
                    {[theme.colors.primary, theme.colors.secondary, theme.colors.accent].map(
                      (color, i) => (
                        <div
                          key={i}
                          className="h-6 w-6 rounded-full border-2 border-white/50"
                          style={{ backgroundColor: color }}
                        />
                      )
                    )}
                  </div>
                </button>
              );
            })}
          </div>
        </div>
      )}
    </div>
  );
};
```

</details>

**Key Points**:
- Themes are defined INLINE (no external imports needed)
- Fixed position top-left
- Dropdown panel with all 5 themes
- Active theme highlighted with glow effect

---

### Step 2: Create Glassmorphic Device Card

**File**: `src/features/control/components/glassmorphic-device-card.tsx`

**Important Changes from Original Card**:
- NO quick action buttons (removed to avoid repetition)
- Shows power state indicator (glowing dot)
- Shows channel badge
- Shows timestamp
- Only shows "Controller Offline" warning when controller is unreachable
- Min-height: 160px (compact)

<details>
<summary>Full code (click to expand)</summary>

```typescript
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
```

</details>

---

### Step 3: Create Glassmorphic Action Toolbar

**File**: `src/features/control/components/glassmorphic-action-toolbar.tsx`

**Features**:
- Fixed top-right position
- All bulk control actions (Power, Channel, Volume, Identify)
- Theme-aware styling
- Large 56px touch targets
- Color-coded action buttons
- Select All checkbox

<details>
<summary>Full code (click to expand)</summary>

```typescript
import { useState } from 'react';
import { sendDiagnosticSignal, sendBulkCommand } from '@/features/devices/api/devices-api';

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
  tags: any[];
  lastSeen: string;
  isOnline: boolean;
  defaultChannel: string | null;
}

interface GlassmorphicActionToolbarProps {
  selectedRows: PortRow[];
  totalRows: number;
  onOpenChannelModal: () => void;
  toggleAll: () => void;
  theme: Theme;
}

export const GlassmorphicActionToolbar = ({
  selectedRows,
  totalRows,
  onOpenChannelModal,
  toggleAll,
  theme,
}: GlassmorphicActionToolbarProps) => {
  const count = selectedRows.length;
  const [isProcessing, setIsProcessing] = useState(false);

  const sendBulkAction = async (command: string) => {
    if (count === 0 || isProcessing) return;

    setIsProcessing(true);
    try {
      const targets = selectedRows.map(row => ({
        hostname: row.hostname,
        port: row.portNumber
      }));

      const response = await sendBulkCommand({
        targets,
        command,
        priority: 5
      });

      console.log(`Queued ${response.queued_count} commands (batch ${response.batch_id})`);
    } catch (error) {
      console.error('Failed to send bulk command:', error);
    } finally {
      setIsProcessing(false);
    }
  };

  const handleDefaultChannel = async () => {
    if (count === 0 || isProcessing) return;

    setIsProcessing(true);
    try {
      const channelGroups = new Map<string, typeof selectedRows>();

      selectedRows.forEach(row => {
        if (row.defaultChannel) {
          const existing = channelGroups.get(row.defaultChannel) || [];
          existing.push(row);
          channelGroups.set(row.defaultChannel, existing);
        }
      });

      if (channelGroups.size === 0) {
        console.log('No devices with default channels configured');
        setIsProcessing(false);
        return;
      }

      const responses = await Promise.all(
        Array.from(channelGroups.entries()).map(([channel, rows]) =>
          sendBulkCommand({
            targets: rows.map(row => ({ hostname: row.hostname, port: row.portNumber })),
            command: 'channel',
            channel,
            priority: 5
          })
        )
      );

      const totalQueued = responses.reduce((sum, r) => sum + r.queued_count, 0);
      console.log(`Queued default channel changes for ${totalQueued} devices`);
    } catch (error) {
      console.error('Failed to send default channel commands:', error);
    } finally {
      setIsProcessing(false);
    }
  };

  const handleIdentify = async () => {
    if (count === 0 || isProcessing) return;

    setIsProcessing(true);
    try {
      const uniqueHostnames = [...new Set(selectedRows.map(row => row.hostname))];
      await Promise.all(
        uniqueHostnames.map(hostname => sendDiagnosticSignal(hostname, 0, 1))
      );
    } catch (error) {
      console.error('Failed to send diagnostic signal:', error);
    } finally {
      setIsProcessing(false);
    }
  };

  const allSelected = totalRows > 0 && selectedRows.length === totalRows;

  return (
    <div
      className="fixed right-6 top-6 z-30 w-64 rounded-3xl shadow-2xl backdrop-blur-xl"
      style={{
        backgroundColor: theme.colors.cardBg,
        border: `2px solid ${theme.colors.cardBorder}`,
      }}
    >
      {/* Header with Select All */}
      <div
        className="border-b px-6 py-4"
        style={{ borderColor: theme.colors.cardBorder }}
      >
        <div className="flex items-center justify-between">
          <div>
            <div
              className="text-lg font-bold"
              style={{ color: theme.colors.textPrimary }}
            >
              {count > 0 ? `${count} Selected` : 'Actions'}
            </div>
            <div
              className="text-sm"
              style={{ color: theme.colors.textSecondary }}
            >
              {count > 0 ? `${count} device${count === 1 ? '' : 's'}` : 'Select devices'}
            </div>
          </div>
          <label className="flex cursor-pointer items-center gap-2">
            <span
              className="text-sm font-semibold"
              style={{ color: theme.colors.textPrimary }}
            >
              All
            </span>
            <input
              type="checkbox"
              checked={allSelected}
              onChange={toggleAll}
              className="h-5 w-5 cursor-pointer rounded transition-all"
              style={{
                accentColor: theme.colors.primary,
              }}
            />
          </label>
        </div>
      </div>

      {/* Actions */}
      <div className="flex flex-col gap-2 p-4">
        <div
          className="px-2 py-1 text-xs font-bold uppercase tracking-wider"
          style={{ color: theme.colors.textSecondary }}
        >
          Power
        </div>
        <ActionButton
          label="Power On"
          icon="⚡"
          onClick={() => sendBulkAction('power_on')}
          disabled={count === 0 || isProcessing}
          theme={theme}
          variant="success"
        />
        <ActionButton
          label="Power Off"
          icon="⚡"
          onClick={() => sendBulkAction('power_off')}
          disabled={count === 0 || isProcessing}
          theme={theme}
          variant="danger"
        />
        <ActionButton
          label="Power Toggle"
          icon="⚡"
          onClick={() => sendBulkAction('power')}
          disabled={count === 0 || isProcessing}
          theme={theme}
        />

        <div
          className="mt-3 px-2 py-1 text-xs font-bold uppercase tracking-wider"
          style={{ color: theme.colors.textSecondary }}
        >
          Channel
        </div>
        <ActionButton
          label="Select Channel"
          icon="📺"
          onClick={onOpenChannelModal}
          disabled={count === 0 || isProcessing}
          theme={theme}
        />
        <ActionButton
          label="Default Channel"
          icon="🏠"
          onClick={handleDefaultChannel}
          disabled={count === 0 || isProcessing}
          theme={theme}
        />

        <div
          className="mt-3 px-2 py-1 text-xs font-bold uppercase tracking-wider"
          style={{ color: theme.colors.textSecondary }}
        >
          Volume
        </div>
        <ActionButton
          label="Mute Toggle"
          icon="🔇"
          onClick={() => sendBulkAction('mute')}
          disabled={count === 0 || isProcessing}
          theme={theme}
        />
        <ActionButton
          label="Volume +"
          icon="🔊"
          onClick={() => sendBulkAction('volume_up')}
          disabled={count === 0 || isProcessing}
          theme={theme}
        />
        <ActionButton
          label="Volume −"
          icon="🔉"
          onClick={() => sendBulkAction('volume_down')}
          disabled={count === 0 || isProcessing}
          theme={theme}
        />

        <div
          className="mt-3 border-t pt-3"
          style={{ borderColor: theme.colors.cardBorder }}
        >
          <ActionButton
            label={isProcessing ? "Processing..." : "Identify (ID)"}
            icon="🔍"
            onClick={handleIdentify}
            disabled={count === 0 || isProcessing}
            theme={theme}
            variant="accent"
          />
        </div>
      </div>
    </div>
  );
};

const ActionButton = ({
  label,
  icon,
  onClick,
  disabled = false,
  theme,
  variant,
}: {
  label: string;
  icon?: string;
  onClick?: () => void;
  disabled?: boolean;
  theme: Theme;
  variant?: 'success' | 'danger' | 'accent';
}) => {
  const getVariantColor = () => {
    switch (variant) {
      case 'success':
        return theme.colors.success;
      case 'danger':
        return theme.colors.danger;
      case 'accent':
        return theme.colors.accent;
      default:
        return theme.colors.primary;
    }
  };

  const variantColor = getVariantColor();

  return (
    <button
      type="button"
      onClick={onClick}
      disabled={disabled}
      className={`min-h-[56px] w-full rounded-xl border-2 px-4 py-3 text-left text-base font-bold transition-all ${
        disabled
          ? 'cursor-not-allowed opacity-40'
          : 'hover:scale-[1.02] active:scale-[0.98]'
      }`}
      style={{
        backgroundColor: disabled ? 'rgba(0, 0, 0, 0.2)' : `${variantColor}30`,
        borderColor: disabled ? theme.colors.cardBorder : variantColor,
        color: disabled ? theme.colors.textSecondary : theme.colors.textPrimary,
        boxShadow: disabled ? 'none' : `0 4px 15px ${variantColor}30`,
      }}
    >
      <div className="flex items-center gap-2">
        {icon && <span className="text-xl">{icon}</span>}
        <span>{label}</span>
      </div>
    </button>
  );
};
```

</details>

---

### Step 4: Create Auth Layout Wrapper

**File**: `src/features/control/pages/control-demo-layout.tsx`

**Purpose**: Wraps the demo page with authentication check (redirects to login if not authenticated)

```typescript
import { Outlet, Navigate, useLocation } from 'react-router-dom';
import { useAuth } from '../../auth/context/auth-context';

export const ControlDemoLayout = () => {
  const location = useLocation();
  const { isAuthenticated, isLoading } = useAuth();

  // Show loading state while checking authentication
  if (isLoading) {
    return (
      <div className="flex min-h-screen items-center justify-center bg-slate-900">
        <div className="text-center">
          <div className="inline-block h-8 w-8 animate-spin rounded-full border-4 border-solid border-rose-600 border-r-transparent"></div>
          <p className="mt-4 text-sm text-slate-300">Loading...</p>
        </div>
      </div>
    );
  }

  // Redirect to login if not authenticated
  if (!isAuthenticated) {
    return <Navigate to="/login" state={{ from: location }} replace />;
  }

  // Just render the outlet with no wrapper - the demo page handles its own styling
  return <Outlet />;
};
```

---

### Step 5: Create Main Demo Page

**File**: `src/features/control/pages/control-demo-page.tsx`

**Note**: This is a LARGE file. Copy the entire theme type and themes array from theme-selector.tsx into the top of this file.

Key sections:
1. **Imports** - All necessary hooks and components
2. **Theme type definition** (INLINE - copy from theme-selector)
3. **Themes array** (INLINE - copy all 5 themes)
4. **PortRow and VirtualDevice interfaces**
5. **buildRows function** (copy from original control-page.tsx)
6. **Component state** (theme, selectedIds, filters, etc.)
7. **Helper functions** (toggleSelection, toggleAll, etc.)
8. **Render** - Full page layout with:
   - Animated gradient background
   - Theme selector (top-left)
   - Action toolbar (top-right)
   - Header section
   - Queue status bar
   - Filter/search bar
   - Location-grouped device cards

**CRITICAL**: Add padding to the main content to avoid overlap with action toolbar:

```tsx
{/* Main Content */}
<div className="mx-auto max-w-[1600px] px-6 py-6 pr-80">  {/* NOTE: pr-80 for toolbar space */}
```

<details>
<summary>Key snippet - Padding fix (click to expand)</summary>

```tsx
return (
  <div
    className="min-h-screen transition-all duration-700"
    style={{
      background: `linear-gradient(135deg, ${currentTheme.colors.gradientFrom}, ${currentTheme.colors.gradientVia || currentTheme.colors.gradientTo}, ${currentTheme.colors.gradientTo})`,
    }}
  >
    {/* Theme Selector */}
    <ThemeSelector currentTheme={currentTheme} onThemeChange={setCurrentTheme} />

    {/* Action Toolbar */}
    <GlassmorphicActionToolbar
      selectedRows={selectedRows}
      totalRows={displayRows.length}
      onOpenChannelModal={() => setShowChannelModal(true)}
      toggleAll={toggleAll}
      theme={currentTheme}
    />

    {/* Main Content - IMPORTANT: pr-80 to avoid toolbar overlap */}
    <div className="mx-auto max-w-[1600px] px-6 py-6 pr-80">
      {/* Rest of content */}
    </div>
  </div>
);
```

</details>

Due to size, reference the original file at: `src/features/control/pages/control-demo-page.tsx` (lines 1-700+)

---

### Step 6: Update Router

**File**: `src/app/router.tsx`

Add imports:
```typescript
import { ControlDemoPage } from '../features/control/pages/control-demo-page';
import { ControlDemoLayout } from '../features/control/pages/control-demo-layout';
```

Add route (after the /control route):
```typescript
{
  path: '/control-demo',
  element: <ControlDemoLayout />,
  children: [{ index: true, element: <ControlDemoPage /> }],
},
```

---

## Common Issues & Solutions

### Issue 1: Module Export Errors

**Symptom**: `The requested module does not provide an export named 'Theme'`

**Solution**: DO NOT create a separate `types/themes.ts` file. Instead, INLINE the Theme type definition at the top of each component file that needs it.

### Issue 2: Vite Cache Issues

**Solution**:
```bash
rm -rf node_modules/.vite
npm run dev
```

Hard refresh browser: `Ctrl+Shift+R` (Windows) or `Cmd+Shift+R` (Mac)

### Issue 3: Content Hidden Under Toolbar

**Symptom**: Device cards hidden behind the action toolbar

**Solution**: Add right padding to main content container:
```tsx
<div className="mx-auto max-w-[1600px] px-6 py-6 pr-80">
```

### Issue 4: Theme Not Changing

**Symptom**: Theme selector shows themes but clicking doesn't change

**Solution**: Ensure `currentTheme` state is passed to ALL components (ThemeSelector, ActionToolbar, DeviceCard)

---

## Testing Checklist

After implementation, verify:

- [ ] Page loads at `/control-demo` without errors
- [ ] Theme selector appears in top-left
- [ ] Action toolbar appears in top-right
- [ ] Can switch between all 5 themes
- [ ] Device cards display with power indicators
- [ ] Can select/deselect individual devices
- [ ] "Select All" checkbox works
- [ ] Location headers have Power On/Off buttons
- [ ] Action toolbar buttons are enabled when devices selected
- [ ] Content doesn't overlap with action toolbar (check right padding)
- [ ] Channel modal opens when "Select Channel" clicked
- [ ] Bulk commands work (Power On/Off, Volume, etc.)

---

## Performance Notes

- Uses existing hooks (no data duplication)
- React.memo and useMemo for optimization
- Smooth 60fps animations with CSS transitions
- Backdrop-blur for glassmorphism effect (requires modern browser)

---

## Browser Requirements

- Chrome/Edge 90+
- Firefox 88+
- Safari 14+
- Must support `backdrop-filter` CSS property

---

## Future Enhancements

- Save theme preference to localStorage
- Add swipe gestures on cards
- Implement haptic feedback for touch devices
- Add custom theme builder UI
- Virtual scrolling for 100+ devices
- Animation speed settings

---

## File Size Reference

- `theme-selector.tsx`: ~300 lines (includes 5 themes)
- `glassmorphic-device-card.tsx`: ~200 lines
- `glassmorphic-action-toolbar.tsx`: ~350 lines
- `control-demo-layout.tsx`: ~30 lines
- `control-demo-page.tsx`: ~700 lines

**Total**: ~1,580 lines of code

---

## Quick Start Commands

```bash
# Navigate to frontend
cd frontend-v2

# Create component files
mkdir -p src/features/control/components
touch src/features/control/components/theme-selector.tsx
touch src/features/control/components/glassmorphic-device-card.tsx
touch src/features/control/components/glassmorphic-action-toolbar.tsx

# Create page files
mkdir -p src/features/control/pages
touch src/features/control/pages/control-demo-layout.tsx
touch src/features/control/pages/control-demo-page.tsx

# Start dev server
npm run dev
```

---

## Support

If you encounter issues after recreating from scratch:

1. Check browser console for errors
2. Verify all imports are correct
3. Ensure Theme type is inlined (not imported)
4. Clear Vite cache: `rm -rf node_modules/.vite`
5. Hard refresh browser
6. Check git diff to see what changed

---

**Last Updated**: 2025-10-12
**Author**: Claude Code Assistant
**Version**: 1.0
