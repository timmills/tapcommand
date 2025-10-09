import { apiClient } from '@/lib/axios';
import type { DiscoveredDevice } from '@/types';

interface DiscoveryServiceResponse {
  devices: DiscoveredDevice[];
}

export interface AllDevicesFilters {
  show_esphome?: boolean;
  show_network?: boolean;
  show_managed?: boolean;
  show_hidden?: boolean;
}

export const fetchDiscoveredDevices = async (): Promise<DiscoveredDevice[]> => {
  // Use database-backed discovery endpoint instead of in-memory mDNS-only endpoint
  // This ensures we see devices that have been discovered but may not be actively broadcasting mDNS
  const response = await apiClient.get<DiscoveredDevice[]>('/api/v1/management/discovered');
  return response.data ?? [];
};

export const fetchAllDevices = async (filters: AllDevicesFilters = {}): Promise<DiscoveredDevice[]> => {
  const params = new URLSearchParams();
  if (filters.show_esphome !== undefined) params.append('show_esphome', String(filters.show_esphome));
  if (filters.show_network !== undefined) params.append('show_network', String(filters.show_network));
  if (filters.show_managed !== undefined) params.append('show_managed', String(filters.show_managed));
  if (filters.show_hidden !== undefined) params.append('show_hidden', String(filters.show_hidden));

  const response = await apiClient.get<DiscoveredDevice[]>(`/api/v1/management/all-devices?${params.toString()}`);
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
