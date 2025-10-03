import { useEffect, useMemo, useState } from 'react';
import {
  useChannelLocations,
  useChannelGroups,
  useSelectChannelLocation,
  useUpdateChannelVisibility,
} from '../hooks/use-channels';
import type { ChannelRecord } from '@/types';

export const SettingsPage = () => {
  return (
    <section className="space-y-6">
      <header>
        <h2 className="text-lg font-semibold text-slate-900">Channels</h2>
        <p className="text-sm text-slate-500">
          Configure channel visibility and broadcast region for your venue.
        </p>
      </header>

      <ChannelManagementPanel />
    </section>
  );
};

const ChannelManagementPanel = () => {
  const locationsQuery = useChannelLocations();
  const selectLocation = useSelectChannelLocation();
  const selectedAvailability = locationsQuery.data?.selected ?? undefined;
  const groupsQuery = useChannelGroups(selectedAvailability);
  const updateChannels = useUpdateChannelVisibility();

  const [channelState, setChannelState] = useState<Record<number, boolean>>({});
  const [initialState, setInitialState] = useState<Record<number, boolean>>({});
  const [lastResult, setLastResult] = useState<string | null>(null);

  const allChannels: ChannelRecord[] = useMemo(() => {
    if (!groupsQuery.data) return [];
    const { recommended, other_fta, foxtel, inhouse } = groupsQuery.data;
    return [...recommended, ...other_fta, ...foxtel, ...inhouse];
  }, [groupsQuery.data]);

  useEffect(() => {
    if (!groupsQuery.data) return;
    const base: Record<number, boolean> = {};
    groupsQuery.data.recommended.forEach((channel) => {
      base[channel.id] = !channel.disabled;
    });
    groupsQuery.data.other_fta.forEach((channel) => {
      base[channel.id] = !channel.disabled;
    });
    groupsQuery.data.foxtel.forEach((channel) => {
      base[channel.id] = !channel.disabled;
    });
    groupsQuery.data.inhouse.forEach((channel) => {
      base[channel.id] = !channel.disabled;
    });
    setChannelState(base);
    setInitialState(base);
  }, [groupsQuery.data]);

  const isDirty = useMemo(() => {
    if (!allChannels.length) return false;
    return allChannels.some((channel) => {
      const current = channelState[channel.id];
      const initial = initialState[channel.id];
      return typeof current === 'boolean' && current !== initial;
    });
  }, [allChannels, channelState, initialState]);

  const toggleChannel = (channelId: number, enabled: boolean) => {
    setChannelState((prev) => ({ ...prev, [channelId]: enabled }));
    setLastResult(null);
  };

  const applyBulk = (channels: ChannelRecord[], enabled: boolean) => {
    setChannelState((prev) => {
      const next = { ...prev };
      channels.forEach((channel) => {
        next[channel.id] = enabled;
      });
      return next;
    });
    setLastResult(null);
  };

  const handleSave = async () => {
    if (!isDirty || updateChannels.isPending) return;

    const enableIds: number[] = [];
    const disableIds: number[] = [];

    allChannels.forEach((channel) => {
      const start = initialState[channel.id];
      const current = channelState[channel.id];
      if (typeof current !== 'boolean' || typeof start !== 'boolean') return;
      if (current && !start) {
        enableIds.push(channel.id);
      } else if (!current && start) {
        disableIds.push(channel.id);
      }
    });

    if (enableIds.length === 0 && disableIds.length === 0) {
      setLastResult('No changes to save.');
      return;
    }

    try {
      await updateChannels.mutateAsync({ enable_ids: enableIds, disable_ids: disableIds });
      setLastResult('Channel visibility updated.');
    } catch (error) {
      const message = error instanceof Error ? error.message : 'Failed to update channels.';
      setLastResult(message);
    }
  };

  const handleReset = () => {
    setChannelState(initialState);
    setLastResult(null);
  };

  const setLocation = async (availability: string) => {
    try {
      await selectLocation.mutateAsync(availability);
      setLastResult(null);
    } catch (error) {
      const message = error instanceof Error ? error.message : 'Failed to change location.';
      setLastResult(message);
    }
  };

  return (
    <div className="space-y-6">
      <div className="rounded-lg border border-slate-200 bg-white p-4 shadow-sm">
        <div className="flex flex-wrap items-center justify-between gap-3">
          <div>
            <h3 className="text-sm font-semibold text-slate-900">Broadcast region</h3>
            <p className="text-xs text-slate-500">
              Select the venue’s location to surface the local FTA multiplex. Foxtel and in-house channels remain available
              regardless of location.
            </p>
          </div>
          <div>
            <label className="flex items-center gap-2 text-xs font-medium text-slate-600">
              Location
              <select
                value={selectedAvailability ?? ''}
                onChange={(event) => setLocation(event.target.value)}
                disabled={locationsQuery.isLoading || selectLocation.isPending}
                className="rounded-md border border-slate-300 px-3 py-2 text-sm text-slate-900 shadow-sm focus:border-brand-500 focus:outline-none focus:ring-1 focus:ring-brand-500"
              >
                {locationsQuery.data?.locations.map((location) => (
                  <option key={location.availability} value={location.availability}>
                    {location.display_name}
                  </option>
                )) ?? (
                  <option value="">Loading…</option>
                )}
              </select>
            </label>
          </div>
        </div>
      </div>

      {groupsQuery.isLoading ? (
        <div className="rounded-lg border border-dashed border-slate-300 bg-white p-8 text-sm text-slate-500">
          Loading channel lists…
        </div>
      ) : groupsQuery.isError ? (
        <div className="rounded-lg border border-rose-200 bg-rose-50 p-4 text-sm text-rose-700">
          Failed to load channels. {groupsQuery.error instanceof Error ? groupsQuery.error.message : 'Please try again.'}
        </div>
      ) : groupsQuery.data ? (
        <div className="space-y-4">
          <ChannelSection
            title="Recommended (FTA)"
            description="Core multiplex for the selected region."
            channels={groupsQuery.data.recommended}
            channelState={channelState}
            onToggle={toggleChannel}
            onBulkEnable={() => applyBulk(groupsQuery.data.recommended, true)}
            onBulkDisable={() => applyBulk(groupsQuery.data.recommended, false)}
          />
          <ChannelSection
            title="Other FTA networks"
            description="Additional services that may not broadcast in your area."
            channels={groupsQuery.data.other_fta}
            channelState={channelState}
            onToggle={toggleChannel}
          />
          <ChannelSection
            title="Foxtel"
            description="Foxtel services (requires the venue’s head-end)."
            channels={groupsQuery.data.foxtel}
            channelState={channelState}
            onToggle={toggleChannel}
          />
          <ChannelSection
            title="In-house"
            description="Venue-only loops or internal signage channels."
            channels={groupsQuery.data.inhouse}
            channelState={channelState}
            onToggle={toggleChannel}
          />
        </div>
      ) : (
        <div className="rounded-lg border border-dashed border-slate-300 bg-white p-8 text-sm text-slate-500">
          No channels available.
        </div>
      )}

      <div className="flex flex-wrap items-center justify-between gap-3">
        <div className="text-xs text-slate-500">
          {lastResult && <span className="text-slate-600">{lastResult}</span>}
        </div>
        <div className="flex gap-2">
          <button
            type="button"
            onClick={handleReset}
            disabled={!isDirty}
            className="rounded-md border border-slate-300 px-3 py-2 text-xs font-medium text-slate-600 transition hover:bg-slate-50 disabled:cursor-not-allowed disabled:border-slate-200 disabled:text-slate-300"
          >
            Reset
          </button>
          <button
            type="button"
            onClick={handleSave}
            disabled={!isDirty || updateChannels.isPending}
            className="rounded-md bg-brand-500 px-4 py-2 text-sm font-medium text-white shadow-sm transition hover:bg-brand-600 disabled:cursor-not-allowed disabled:bg-brand-300"
          >
            {updateChannels.isPending ? 'Saving…' : 'Save changes'}
          </button>
        </div>
      </div>
    </div>
  );
};

const ChannelSection = ({
  title,
  description,
  channels,
  channelState,
  onToggle,
  onBulkEnable,
  onBulkDisable,
}: {
  title: string;
  description?: string;
  channels: ChannelRecord[];
  channelState: Record<number, boolean>;
  onToggle: (channelId: number, enabled: boolean) => void;
  onBulkEnable?: () => void;
  onBulkDisable?: () => void;
}) => {
  if (!channels.length) {
    return null;
  }

  return (
    <div className="rounded-lg border border-slate-200 bg-white shadow-sm">
      <div className="flex flex-wrap items-center justify-between gap-3 border-b border-slate-200 px-4 py-3">
        <div>
          <h4 className="text-sm font-semibold text-slate-900">{title}</h4>
          {description ? <p className="text-xs text-slate-500">{description}</p> : null}
        </div>
        {(onBulkEnable || onBulkDisable) && (
          <div className="flex gap-2 text-xs text-slate-600">
            {onBulkEnable ? (
              <button
                type="button"
                onClick={onBulkEnable}
                className="rounded border border-slate-300 px-2 py-1 transition hover:bg-slate-50"
              >
                Enable all
              </button>
            ) : null}
            {onBulkDisable ? (
              <button
                type="button"
                onClick={onBulkDisable}
                className="rounded border border-slate-300 px-2 py-1 transition hover:bg-slate-50"
              >
                Disable all
              </button>
            ) : null}
          </div>
        )}
      </div>
      <div className="divide-y divide-slate-100">
        {channels.map((channel) => {
          const enabled = channelState[channel.id] ?? !channel.disabled;
          const labelParts = [channel.channel_name];
          if (channel.lcn) {
            labelParts.push(`LCN ${channel.lcn}`);
          }
          if (channel.foxtel_number) {
            labelParts.push(`Foxtel ${channel.foxtel_number}`);
          }
          return (
            <label key={channel.id} className="flex items-center justify-between gap-2 px-4 py-3 text-sm">
              <div>
                <div className="font-medium text-slate-900">{labelParts.join(' · ')}</div>
                <div className="text-xs text-slate-500">
                  {channel.platform}
                  {channel.availability && channel.platform === 'FTA' ? ` • ${channel.availability}` : ''}
                </div>
              </div>
              <input
                type="checkbox"
                checked={enabled}
                onChange={(event) => onToggle(channel.id, event.target.checked)}
                className="h-4 w-4 rounded border-slate-300 text-brand-600 focus:ring-brand-500"
              />
            </label>
          );
        })}
      </div>
    </div>
  );
};

