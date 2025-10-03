/**
 * Scheduling System Types
 */

export interface ScheduleAction {
  type: 'power' | 'mute' | 'volume_up' | 'volume_down' | 'channel' | 'default_channel';
  value?: string; // For channel: channel ID
  repeat?: number; // For volume: 1-10
  wait_after?: number; // Seconds
}

export interface ScheduleTarget {
  type: 'all' | 'selection' | 'tag' | 'location';
  device_ids?: number[]; // IRPort IDs for selection
  tag_ids?: number[]; // Tag IDs for tag
  locations?: string[]; // Location names for location
}

export interface Schedule {
  id: number;
  name: string;
  description?: string;
  cron_expression: string;
  target_type: string;
  target_data?: Record<string, any>;
  actions: ScheduleAction[];
  is_active: boolean;
  last_run?: string; // ISO datetime
  next_run?: string; // ISO datetime
  created_at: string;
  updated_at: string;
}

export interface ScheduleExecution {
  id: number;
  schedule_id: number;
  batch_id: string;
  executed_at: string;
  total_commands?: number;
  succeeded?: number;
  failed?: number;
  avg_execution_time_ms?: number;
}

export interface CreateScheduleRequest {
  name: string;
  description?: string;
  cron_expression: string;
  target_type: string;
  target_data?: Record<string, any>;
  actions: ScheduleAction[];
  is_active: boolean;
}

export interface UpdateScheduleRequest {
  name?: string;
  description?: string;
  cron_expression?: string;
  target_type?: string;
  target_data?: Record<string, any>;
  actions?: ScheduleAction[];
  is_active?: boolean;
}

export interface RunNowResponse {
  batch_id: string;
  queued_count: number;
  command_ids: number[];
}

// Wait time options (in seconds)
export const WAIT_TIME_OPTIONS = [
  { value: 0, label: 'None' },
  { value: 5, label: '5 seconds' },
  { value: 10, label: '10 seconds' },
  { value: 15, label: '15 seconds' },
  { value: 30, label: '30 seconds' },
  { value: 60, label: '1 minute' },
  { value: 120, label: '2 minutes' },
  { value: 300, label: '5 minutes' },
  { value: 600, label: '10 minutes' },
  { value: 900, label: '15 minutes' },
  { value: 3600, label: '1 hour' },
  { value: 10800, label: '3 hours' },
  { value: 18000, label: '5 hours' },
] as const;

// Cron presets
export const CRON_PRESETS = [
  { value: '0 8 * * *', label: 'Daily at 8:00 AM' },
  { value: '0 8 * * 1-5', label: 'Weekdays at 8:00 AM' },
  { value: '0 10 * * 6,0', label: 'Weekends at 10:00 AM' },
  { value: '0 9 * * 1', label: 'Every Monday at 9:00 AM' },
  { value: '0 12 1 * *', label: 'First day of month at 12:00 PM' },
  { value: '0 */2 * * *', label: 'Every 2 hours' },
  { value: '*/30 * * * *', label: 'Every 30 minutes' },
  { value: '30 17 * * *', label: 'Daily at 5:30 PM' },
] as const;

// Action type labels
export const ACTION_TYPE_LABELS: Record<ScheduleAction['type'], string> = {
  power: 'Power',
  mute: 'Mute',
  volume_up: 'Volume Up',
  volume_down: 'Volume Down',
  channel: 'Channel',
  default_channel: 'Default Channel',
};

// Power value options
export const POWER_OPTIONS = [
  { value: 'on', label: 'ON' },
  { value: 'off', label: 'OFF' },
  { value: 'toggle', label: 'Toggle' },
] as const;

// Mute value options
export const MUTE_OPTIONS = [
  { value: 'on', label: 'ON' },
  { value: 'off', label: 'OFF' },
  { value: 'toggle', label: 'Toggle' },
] as const;

// Volume repeat options
export const VOLUME_REPEAT_OPTIONS = Array.from({ length: 10 }, (_, i) => ({
  value: i + 1,
  label: `${i + 1} time${i === 0 ? '' : 's'}`,
}));
