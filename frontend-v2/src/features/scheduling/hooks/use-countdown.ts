/**
 * Countdown timer hook for next schedule
 */

import { useState, useEffect } from 'react';

export function useCountdown(targetDate: string | null | undefined): string {
  const [countdown, setCountdown] = useState<string>('');

  useEffect(() => {
    if (!targetDate) {
      setCountdown('');
      return;
    }

    const updateCountdown = () => {
      const now = new Date().getTime();
      const target = new Date(targetDate).getTime();
      const diff = target - now;

      if (diff <= 0) {
        setCountdown('Now');
        return;
      }

      const hours = Math.floor(diff / (1000 * 60 * 60));
      const minutes = Math.floor((diff % (1000 * 60 * 60)) / (1000 * 60));
      const seconds = Math.floor((diff % (1000 * 60)) / 1000);

      if (hours > 24) {
        const days = Math.floor(hours / 24);
        setCountdown(`${days}d ${hours % 24}h`);
      } else if (hours > 0) {
        setCountdown(`${hours}h ${minutes}m`);
      } else if (minutes > 0) {
        setCountdown(`${minutes}m ${seconds}s`);
      } else {
        setCountdown(`${seconds}s`);
      }
    };

    // Update immediately
    updateCountdown();

    // Update every second
    const interval = setInterval(updateCountdown, 1000);

    return () => clearInterval(interval);
  }, [targetDate]);

  return countdown;
}

export function formatNextRun(nextRun: string | null | undefined): string {
  if (!nextRun) return 'Not scheduled';

  const date = new Date(nextRun);
  const now = new Date();

  // Check if today
  const isToday = date.toDateString() === now.toDateString();

  // Check if tomorrow
  const tomorrow = new Date(now);
  tomorrow.setDate(tomorrow.getDate() + 1);
  const isTomorrow = date.toDateString() === tomorrow.toDateString();

  const timeString = date.toLocaleTimeString('en-US', {
    hour: 'numeric',
    minute: '2-digit',
    hour12: true,
  });

  if (isToday) {
    return `Today at ${timeString}`;
  } else if (isTomorrow) {
    return `Tomorrow at ${timeString}`;
  } else {
    const dateString = date.toLocaleDateString('en-US', {
      month: 'short',
      day: 'numeric',
    });
    return `${dateString} at ${timeString}`;
  }
}
