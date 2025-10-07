import { apiClient } from '@/lib/axios';
import type { DiscoveredDevice } from '@/types';

interface DiscoveryServiceResponse {
  devices: DiscoveredDevice[];
}

export const fetchDiscoveredDevices = async (): Promise<DiscoveredDevice[]> => {
  // Use database-backed discovery endpoint instead of in-memory mDNS-only endpoint
  // This ensures we see devices that have been discovered but may not be actively broadcasting mDNS
  const response = await apiClient.get<DiscoveredDevice[]>('/api/v1/management/discovered');
  return response.data ?? [];
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
