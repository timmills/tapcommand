import { useState, useEffect } from 'react';
import { cronToHuman, buildDailyCron, parseDaysOfWeek, DAY_NAMES, isValidCron } from '../utils/cron-utils';

interface CronBuilderProps {
  value: string;
  onChange: (cron: string) => void;
}

type FrequencyType = 'daily' | 'weekly' | 'custom';

export function CronBuilder({ value, onChange }: CronBuilderProps) {
  const [frequency, setFrequency] = useState<FrequencyType>('daily');
  const [time, setTime] = useState('08:00');
  const [selectedDays, setSelectedDays] = useState<number[]>([1, 2, 3, 4, 5]); // Mon-Fri
  const [customCron, setCustomCron] = useState(value || '0 8 * * 1-5');

  // Parse initial cron value
  useEffect(() => {
    if (value) {
      const parts = value.split(' ');
      if (parts.length === 5) {
        // Extract time
        const hour = parts[1];
        const minute = parts[0];
        const timeStr = `${hour.padStart(2, '0')}:${minute.padStart(2, '0')}`;
        setTime(timeStr);

        // Check if custom
        const dayOfWeek = parts[4];
        if (dayOfWeek === '*') {
          setFrequency('daily');
          setSelectedDays([0, 1, 2, 3, 4, 5, 6]);
        } else if (dayOfWeek.includes('-') || dayOfWeek.includes(',')) {
          setFrequency('daily');
          try {
            setSelectedDays(parseDaysOfWeek(dayOfWeek));
          } catch {
            setFrequency('custom');
          }
        } else {
          setFrequency('custom');
        }
        setCustomCron(value);
      }
    }
  }, [value]);

  // Update parent when values change
  useEffect(() => {
    if (frequency === 'custom') {
      if (isValidCron(customCron)) {
        onChange(customCron);
      }
    } else {
      const days = frequency === 'daily' ? selectedDays : undefined;
      const cron = buildDailyCron(time, days);
      onChange(cron);
    }
  }, [frequency, time, selectedDays, customCron, onChange]);

  const toggleDay = (day: number) => {
    if (selectedDays.includes(day)) {
      setSelectedDays(selectedDays.filter((d) => d !== day));
    } else {
      setSelectedDays([...selectedDays, day].sort());
    }
  };

  const selectAllDays = () => setSelectedDays([0, 1, 2, 3, 4, 5, 6]);
  const selectWeekdays = () => setSelectedDays([1, 2, 3, 4, 5]);
  const selectWeekends = () => setSelectedDays([0, 6]);

  return (
    <div className="space-y-4">
      {/* Frequency Selection */}
      <div>
        <label className="block text-sm font-medium text-slate-700 mb-2">Frequency</label>
        <div className="flex gap-2">
          <button
            type="button"
            onClick={() => setFrequency('daily')}
            className={`px-4 py-2 text-sm font-medium rounded-md ${
              frequency === 'daily'
                ? 'bg-brand-600 text-white'
                : 'bg-white border border-slate-300 text-slate-700 hover:bg-slate-50'
            }`}
          >
            Daily
          </button>
          <button
            type="button"
            onClick={() => setFrequency('custom')}
            className={`px-4 py-2 text-sm font-medium rounded-md ${
              frequency === 'custom'
                ? 'bg-brand-600 text-white'
                : 'bg-white border border-slate-300 text-slate-700 hover:bg-slate-50'
            }`}
          >
            Custom
          </button>
        </div>
      </div>

      {/* Daily Mode */}
      {frequency === 'daily' && (
        <>
          {/* Time */}
          <div>
            <label className="block text-sm font-medium text-slate-700 mb-2">Time</label>
            <input
              type="time"
              value={time}
              onChange={(e) => setTime(e.target.value)}
              className="block w-full rounded-md border-slate-300 shadow-sm focus:border-brand-500 focus:ring-brand-500"
            />
          </div>

          {/* Days */}
          <div>
            <label className="block text-sm font-medium text-slate-700 mb-2">Days</label>
            <div className="flex gap-2 mb-2">
              <button
                type="button"
                onClick={selectAllDays}
                className="text-xs px-2 py-1 rounded border border-slate-300 hover:bg-slate-50"
              >
                All
              </button>
              <button
                type="button"
                onClick={selectWeekdays}
                className="text-xs px-2 py-1 rounded border border-slate-300 hover:bg-slate-50"
              >
                Weekdays
              </button>
              <button
                type="button"
                onClick={selectWeekends}
                className="text-xs px-2 py-1 rounded border border-slate-300 hover:bg-slate-50"
              >
                Weekends
              </button>
            </div>
            <div className="flex gap-2">
              {DAY_NAMES.map((day, index) => (
                <button
                  key={day}
                  type="button"
                  onClick={() => toggleDay(index)}
                  className={`flex-1 py-2 text-sm font-medium rounded-md ${
                    selectedDays.includes(index)
                      ? 'bg-brand-600 text-white'
                      : 'bg-white border border-slate-300 text-slate-700 hover:bg-slate-50'
                  }`}
                >
                  {day}
                </button>
              ))}
            </div>
          </div>
        </>
      )}

      {/* Custom Mode */}
      {frequency === 'custom' && (
        <div>
          <label className="block text-sm font-medium text-slate-700 mb-2">
            Cron Expression
          </label>
          <input
            type="text"
            value={customCron}
            onChange={(e) => setCustomCron(e.target.value)}
            placeholder="0 8 * * 1-5"
            className="block w-full rounded-md border-slate-300 shadow-sm focus:border-brand-500 focus:ring-brand-500 font-mono text-sm"
          />
          <p className="mt-1 text-xs text-slate-500">
            Format: minute hour day month weekday
          </p>
        </div>
      )}

      {/* Human-readable summary */}
      <div className="rounded-md bg-slate-50 p-3">
        <div className="text-sm font-medium text-slate-700">Schedule:</div>
        <div className="text-sm text-slate-600">
          {frequency === 'custom' ? cronToHuman(customCron) : cronToHuman(buildDailyCron(time, selectedDays))}
        </div>
        <div className="mt-1 text-xs text-slate-500 font-mono">
          {frequency === 'custom' ? customCron : buildDailyCron(time, selectedDays)}
        </div>
      </div>
    </div>
  );
}
