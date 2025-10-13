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
      className="fixed right-6 top-6 z-30 w-56 rounded-2xl shadow-2xl backdrop-blur-xl"
      style={{
        backgroundColor: theme.colors.cardBg,
        border: `2px solid ${theme.colors.cardBorder}`,
      }}
    >
      {/* Header with Select All */}
      <div
        className="border-b px-4 py-3"
        style={{ borderColor: theme.colors.cardBorder }}
      >
        <div className="flex items-center justify-between">
          <div>
            <div
              className="text-base font-bold"
              style={{ color: theme.colors.textPrimary }}
            >
              {count > 0 ? `${count} Selected` : 'Actions'}
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
      <div className="flex flex-col gap-1.5 p-3">
        <div
          className="px-2 py-0.5 text-xs font-bold uppercase tracking-wider"
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
          className="mt-2 px-2 py-0.5 text-xs font-bold uppercase tracking-wider"
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
          className="mt-2 px-2 py-0.5 text-xs font-bold uppercase tracking-wider"
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
          className="mt-2 border-t pt-2"
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
      className={`min-h-[44px] w-full rounded-lg border-2 px-3 py-2 text-left text-sm font-bold transition-all ${
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
        {icon && <span className="text-lg">{icon}</span>}
        <span>{label}</span>
      </div>
    </button>
  );
};
