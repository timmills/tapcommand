import { apiClient } from '@/lib/axios';

export interface AudioZone {
  id: number;
  controller_id: number;
  controller_name: string;
  zone_number: number;
  zone_name: string;
  device_type: string;
  protocol: string;
  volume_level: number | null;
  is_muted: boolean | null;
  is_online: boolean;
  gain_range: [number, number] | null;
  has_mute: boolean;
}

export interface AudioController {
  id: number;
  controller_id: string;
  controller_name: string;
  controller_type: string;
  ip_address: string;
  port: number;
  is_online: boolean;
  total_zones: number;
  zones: AudioZone[];
}

export const audioApi = {
  // List all audio controllers with zones
  getControllers: async (): Promise<AudioController[]> => {
    const response = await apiClient.get('/api/audio/controllers');
    return response.data;
  },

  // List all zones
  getZones: async (controllerId?: string): Promise<AudioZone[]> => {
    const params = controllerId ? { controller_id: controllerId } : {};
    const response = await apiClient.get('/api/audio/zones', { params });
    return response.data;
  },

  // Set zone volume (0-100)
  setVolume: async (zoneId: number, volume: number): Promise<void> => {
    await apiClient.post(`/api/audio/zones/${zoneId}/volume`, { volume });
  },

  // Volume up
  volumeUp: async (zoneId: number): Promise<void> => {
    await apiClient.post(`/api/audio/zones/${zoneId}/volume/up`);
  },

  // Volume down
  volumeDown: async (zoneId: number): Promise<void> => {
    await apiClient.post(`/api/audio/zones/${zoneId}/volume/down`);
  },

  // Toggle mute
  toggleMute: async (zoneId: number): Promise<void> => {
    await apiClient.post(`/api/audio/zones/${zoneId}/mute`);
  },

  // Set mute
  setMute: async (zoneId: number, mute: boolean): Promise<void> => {
    await apiClient.post(`/api/audio/zones/${zoneId}/mute`, { mute });
  },

  // Delete controller
  deleteController: async (controllerId: string): Promise<void> => {
    await apiClient.delete(`/api/audio/controllers/${controllerId}`);
  },

  // Rediscover zones
  rediscoverZones: async (controllerId: string): Promise<void> => {
    await apiClient.post(`/api/audio/controllers/${controllerId}/rediscover`);
  },
};
