import { apiClient } from '@/lib/axios';
import type { DiscoveredDevice } from '@/types';

interface DiscoveryServiceResponse {
  devices: DiscoveredDevice[];
}

export const fetchDiscoveredDevices = async (): Promise<DiscoveredDevice[]> => {
  const response = await apiClient.get<DiscoveryServiceResponse>('/api/v1/devices/discovery/devices');
  return response.data.devices ?? [];
};

export const startDiscovery = async (): Promise<void> => {
  await apiClient.post('/api/v1/devices/discovery/start');
};

export const stopDiscovery = async (): Promise<void> => {
  await apiClient.post('/api/v1/devices/discovery/stop');
};

export const connectDiscoveredDevice = async (
  hostname: string,
  payload: Record<string, unknown> = {},
): Promise<void> => {
  await apiClient.post(`/api/v1/management/manage/${hostname}`, payload);
};
