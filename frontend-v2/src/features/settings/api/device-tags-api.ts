import { apiClient } from '@/lib/axios';
import type { DeviceTag } from '@/types';

export interface DeviceTagPayload {
  name: string;
  color?: string | null;
  description?: string | null;
}

export const fetchDeviceTags = async (): Promise<DeviceTag[]> => {
  const response = await apiClient.get<DeviceTag[]>('/api/v1/settings/tags');
  return response.data;
};

export const createDeviceTag = async (payload: DeviceTagPayload): Promise<DeviceTag> => {
  const response = await apiClient.post<DeviceTag>('/api/v1/settings/tags', payload);
  return response.data;
};

export const updateDeviceTag = async (tagId: number, payload: DeviceTagPayload): Promise<DeviceTag> => {
  const response = await apiClient.put<DeviceTag>(`/api/v1/settings/tags/${tagId}`, payload);
  return response.data;
};

export const deleteDeviceTag = async (tagId: number): Promise<void> => {
  await apiClient.delete(`/api/v1/settings/tags/${tagId}`);
};
