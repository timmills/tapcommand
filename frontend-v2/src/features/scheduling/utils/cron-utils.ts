/**
 * Cron expression utilities
 */

export interface CronParts {
  minute: string;
  hour: string;
  dayOfMonth: string;
  month: string;
  dayOfWeek: string;
}

/**
 * Parse a cron expression into parts
 */
export function parseCron(expression: string): CronParts {
  const parts = expression.split(' ');

  if (parts.length !== 5) {
    throw new Error('Invalid cron expression');
  }

  return {
    minute: parts[0],
    hour: parts[1],
    dayOfMonth: parts[2],
    month: parts[3],
    dayOfWeek: parts[4],
  };
}

/**
 * Build a cron expression from parts
 */
export function buildCron(parts: CronParts): string {
  return `${parts.minute} ${parts.hour} ${parts.dayOfMonth} ${parts.month} ${parts.dayOfWeek}`;
}

/**
 * Convert time (HH:MM) to cron hour and minute
 */
export function timeToCron(time: string): { hour: string; minute: string } {
  const [hour, minute] = time.split(':');
  return {
    hour: hour || '0',
    minute: minute || '0',
  };
}

/**
 * Convert cron hour and minute to time (HH:MM)
 */
export function cronToTime(hour: string, minute: string): string {
  const h = hour === '*' ? '0' : hour;
  const m = minute === '*' ? '0' : minute;
  return `${h.padStart(2, '0')}:${m.padStart(2, '0')}`;
}

/**
 * Convert day of week numbers to names
 */
export const DAY_NAMES = ['Sun', 'Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat'] as const;

/**
 * Parse day of week cron part to array of day numbers
 */
export function parseDaysOfWeek(cronPart: string): number[] {
  if (cronPart === '*') return [0, 1, 2, 3, 4, 5, 6];

  const days: number[] = [];

  // Handle ranges (e.g., "1-5")
  if (cronPart.includes('-')) {
    const [start, end] = cronPart.split('-').map(Number);
    for (let i = start; i <= end; i++) {
      days.push(i);
    }
    return days;
  }

  // Handle comma-separated (e.g., "1,3,5")
  if (cronPart.includes(',')) {
    return cronPart.split(',').map(Number);
  }

  // Single day
  return [Number(cronPart)];
}

/**
 * Build day of week cron part from array of day numbers
 */
export function buildDaysOfWeek(days: number[]): string {
  if (days.length === 7) return '*';
  if (days.length === 0) return '*';

  // Check if consecutive range
  const sorted = [...days].sort((a, b) => a - b);
  let isConsecutive = true;
  for (let i = 1; i < sorted.length; i++) {
    if (sorted[i] !== sorted[i - 1] + 1) {
      isConsecutive = false;
      break;
    }
  }

  if (isConsecutive && sorted.length > 1) {
    return `${sorted[0]}-${sorted[sorted.length - 1]}`;
  }

  return sorted.join(',');
}

/**
 * Convert cron expression to human-readable string
 */
export function cronToHuman(expression: string): string {
  try {
    const parts = parseCron(expression);

    // Get time
    const time = cronToTime(parts.hour, parts.minute);
    const [hour, minute] = time.split(':');
    const hourNum = parseInt(hour, 10);
    const ampm = hourNum >= 12 ? 'PM' : 'AM';
    const hour12 = hourNum % 12 || 12;
    const timeStr = `${hour12}:${minute} ${ampm}`;

    // Check for daily
    if (parts.dayOfMonth === '*' && parts.month === '*' && parts.dayOfWeek === '*') {
      return `Daily at ${timeStr}`;
    }

    // Check for weekdays (1-5)
    if (parts.dayOfWeek === '1-5' && parts.dayOfMonth === '*') {
      return `Weekdays at ${timeStr}`;
    }

    // Check for weekends (6,0 or 0,6)
    if ((parts.dayOfWeek === '6,0' || parts.dayOfWeek === '0,6') && parts.dayOfMonth === '*') {
      return `Weekends at ${timeStr}`;
    }

    // Check for specific days
    if (parts.dayOfWeek !== '*' && parts.dayOfMonth === '*') {
      const days = parseDaysOfWeek(parts.dayOfWeek);
      const dayNames = days.map((d) => DAY_NAMES[d]).join(', ');
      return `${dayNames} at ${timeStr}`;
    }

    // Check for monthly
    if (parts.dayOfMonth !== '*' && parts.month === '*') {
      const day = parts.dayOfMonth;
      return `Monthly on day ${day} at ${timeStr}`;
    }

    // Check for every N hours
    if (parts.hour.includes('*/')) {
      const hours = parts.hour.split('*/')[1];
      return `Every ${hours} hours`;
    }

    // Check for every N minutes
    if (parts.minute.includes('*/')) {
      const minutes = parts.minute.split('*/')[1];
      return `Every ${minutes} minutes`;
    }

    // Default
    return expression;
  } catch (e) {
    return expression;
  }
}

/**
 * Validate cron expression (basic)
 */
export function isValidCron(expression: string): boolean {
  try {
    const parts = expression.split(' ');
    if (parts.length !== 5) return false;

    // Basic validation - just check it has 5 parts
    // Server will do more thorough validation
    return true;
  } catch {
    return false;
  }
}

/**
 * Build daily cron expression
 */
export function buildDailyCron(time: string, days?: number[]): string {
  const { hour, minute } = timeToCron(time);

  if (!days || days.length === 0 || days.length === 7) {
    return `${minute} ${hour} * * *`;
  }

  const dayOfWeek = buildDaysOfWeek(days);
  return `${minute} ${hour} * * ${dayOfWeek}`;
}

/**
 * Build monthly cron expression
 */
export function buildMonthlyCron(time: string, dayOfMonth: number): string {
  const { hour, minute } = timeToCron(time);
  return `${minute} ${hour} ${dayOfMonth} * *`;
}
