import { useState, useEffect, useCallback } from 'react';
import type { Channel, AreaInfo, InHouseChannelCreate, InHouseChannelUpdate } from '../types';

const CHANNELS_API_BASE = 'http://localhost:8000';

export const useChannels = () => {
  const [channels, setChannels] = useState<Channel[]>([]);
  const [areas, setAreas] = useState<AreaInfo[]>([]);
  const [inHouseChannels, setInHouseChannels] = useState<Channel[]>([]);
  const [selectedChannels, setSelectedChannels] = useState<string[]>([]);
  const [selectedAreaName, setSelectedAreaName] = useState<string | null>(null);
  const [editingInHouseChannel, setEditingInHouseChannel] = useState<InHouseChannelCreate | InHouseChannelUpdate | null>(null);
  const [loading, setLoading] = useState(false);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const fetchAreas = useCallback(async () => {
    try {
      const response = await fetch(`${CHANNELS_API_BASE}/api/v1/channels/areas`);
      if (!response.ok) {
        throw new Error(`Failed to fetch areas: ${response.statusText}`);
      }
      const data = await response.json();
      setAreas(data.areas || data);
    } catch (err) {
      const errorMessage = err instanceof Error ? err.message : 'Failed to fetch areas';
      setError(errorMessage);
      console.error('Error fetching areas:', err);
    }
  }, []);

  const fetchChannelsForArea = useCallback(async (areaName: string) => {
    setLoading(true);
    setError(null);
    try {
      // Mock channels data until backend API is implemented
      const mockChannels: Channel[] = [
        {
          id: 1,
          channel_name: "ABC",
          channel_number: "2",
          lcn: "2",
          broadcaster_network: "ABC",
          logo_url: "http://localhost:8000/static/channel-icons/ABC.png",
          local_logo_path: "static/channel-icons/ABC.png",
          platform: "free-to-air",
          disabled: false,
          availability: [areaName],
          description: "Australian Broadcasting Corporation"
        },
        {
          id: 2,
          channel_name: "Nine",
          channel_number: "9",
          lcn: "9",
          broadcaster_network: "Nine",
          logo_url: "http://localhost:8000/static/channel-icons/Nine.png",
          local_logo_path: "static/channel-icons/Nine.png",
          platform: "free-to-air",
          disabled: false,
          availability: [areaName],
          description: "Nine Network"
        },
        {
          id: 3,
          channel_name: "Foxtel Movies",
          channel_number: "101",
          foxtel_number: "101",
          broadcaster_network: "Foxtel",
          platform: "foxtel",
          disabled: false,
          availability: [areaName],
          description: "Foxtel Movies Channel"
        }
      ];

      setChannels(mockChannels);

      const enabledChannelIds = mockChannels
        .filter((channel: Channel) => !channel.disabled)
        .map((channel: Channel) => channel.id.toString());
      setSelectedChannels(enabledChannelIds);
    } catch (err) {
      const errorMessage = err instanceof Error ? err.message : 'Failed to fetch channels for area';
      setError(errorMessage);
      console.error('Error fetching channels for area:', err);
    } finally {
      setLoading(false);
    }
  }, []);

  const fetchInHouseChannels = useCallback(async () => {
    try {
      const response = await fetch(`${CHANNELS_API_BASE}/channels/inhouse`);
      if (!response.ok) {
        throw new Error(`Failed to fetch in-house channels: ${response.statusText}`);
      }
      const data = await response.json();
      setInHouseChannels(data);
    } catch (err) {
      const errorMessage = err instanceof Error ? err.message : 'Failed to fetch in-house channels';
      setError(errorMessage);
      console.error('Error fetching in-house channels:', err);
    }
  }, []);

  const saveAreaChannels = useCallback(async () => {
    if (!selectedAreaName) return;

    setSaving(true);
    setError(null);
    try {
      const channelUpdates = channels.map(channel => ({
        id: channel.id,
        disabled: !selectedChannels.includes(channel.id.toString())
      }));

      const response = await fetch(`${CHANNELS_API_BASE}/channels/bulk-update`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({ channels: channelUpdates }),
      });

      if (!response.ok) {
        throw new Error(`Failed to save channels: ${response.statusText}`);
      }

      await fetchChannelsForArea(selectedAreaName);
    } catch (err) {
      const errorMessage = err instanceof Error ? err.message : 'Failed to save channels';
      setError(errorMessage);
      console.error('Error saving channels:', err);
    } finally {
      setSaving(false);
    }
  }, [selectedAreaName, channels, selectedChannels, fetchChannelsForArea]);

  const saveInHouseChannel = useCallback(async (channelData: InHouseChannelCreate | InHouseChannelUpdate) => {
    setError(null);
    try {
      const isUpdate = 'id' in channelData && channelData.id;
      const url = isUpdate
        ? `${CHANNELS_API_BASE}/channels/inhouse/${channelData.id}`
        : `${CHANNELS_API_BASE}/channels/inhouse`;

      const method = isUpdate ? 'PUT' : 'POST';

      const payload = {
        lcn: channelData.channel_number,
        channel_name: channelData.channel_name,
        broadcaster_network: channelData.broadcaster_network,
        platform: channelData.platform || 'terrestrial'
      };

      const response = await fetch(url, {
        method,
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify(payload),
      });

      if (!response.ok) {
        throw new Error(`Failed to save in-house channel: ${response.statusText}`);
      }

      await fetchInHouseChannels();
    } catch (err) {
      const errorMessage = err instanceof Error ? err.message : 'Failed to save in-house channel';
      setError(errorMessage);
      console.error('Error saving in-house channel:', err);
      throw err;
    }
  }, [fetchInHouseChannels]);

  const deleteInHouseChannel = useCallback(async (channelId: number) => {
    setError(null);
    try {
      const response = await fetch(`${CHANNELS_API_BASE}/channels/inhouse/${channelId}`, {
        method: 'DELETE',
      });

      if (!response.ok) {
        throw new Error(`Failed to delete in-house channel: ${response.statusText}`);
      }

      await fetchInHouseChannels();
    } catch (err) {
      const errorMessage = err instanceof Error ? err.message : 'Failed to delete in-house channel';
      setError(errorMessage);
      console.error('Error deleting in-house channel:', err);
    }
  }, [fetchInHouseChannels]);

  useEffect(() => {
    fetchAreas();
    fetchInHouseChannels();
  }, [fetchAreas, fetchInHouseChannels]);

  useEffect(() => {
    if (selectedAreaName) {
      fetchChannelsForArea(selectedAreaName);
    }
  }, [selectedAreaName, fetchChannelsForArea]);

  return {
    channels,
    setChannels,
    areas,
    inHouseChannels,
    selectedChannels,
    selectedAreaName,
    editingInHouseChannel,
    loading,
    saving,
    error,
    setSelectedChannels,
    setSelectedAreaName,
    setEditingInHouseChannel,
    setChannelsSaving: setSaving,
    setInhouseLoading: setLoading,
    fetchChannelsForArea,
    saveAreaChannels,
    saveInHouseChannel,
    deleteInHouseChannel,
  };
};