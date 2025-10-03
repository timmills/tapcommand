const rtf = new Intl.RelativeTimeFormat('en', { numeric: 'auto' });

const timeDivisions: Array<{ amount: number; name: Intl.RelativeTimeFormatUnit }> = [
  { amount: 60, name: 'seconds' },
  { amount: 60, name: 'minutes' },
  { amount: 24, name: 'hours' },
  { amount: 7, name: 'days' },
  { amount: 4.34524, name: 'weeks' },
  { amount: 12, name: 'months' },
  { amount: Number.POSITIVE_INFINITY, name: 'years' },
];

export const formatRelativeTime = (value: string | null | undefined): string => {
  if (!value) return 'unknown';
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return 'unknown';

  let duration = (date.getTime() - Date.now()) / 1000;

  for (const division of timeDivisions) {
    if (Math.abs(duration) < division.amount) {
      return rtf.format(Math.round(duration), division.name);
    }
    duration /= division.amount;
  }
  return 'unknown';
};

export const formatDateTime = (value: string | null | undefined): string => {
  if (!value) return '—';
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return '—';
  return date.toLocaleString();
};
