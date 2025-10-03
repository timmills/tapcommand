import { apiClient } from '@/lib/axios';
import type { ChannelOption, ManagedDevice } from '@/types';

export interface IRPortUpdatePayload {
  port_number: number;
  connected_device_name?: string | null;
  is_active?: boolean;
  cable_length?: string | null;
  installation_notes?: string | null;
  tag_ids?: number[] | null;
  default_channel?: string | null;
  device_number?: number | null;
}

export interface ManagedDeviceUpdatePayload {
  device_name?: string | null;
  api_key?: string | null;
  venue_name?: string | null;
  location?: string | null;
  notes?: string | null;
  ir_ports?: IRPortUpdatePayload[];
}

export const fetchManagedDevices = async (): Promise<ManagedDevice[]> => {
  const response = await apiClient.get<ManagedDevice[]>('/api/v1/management/managed');
  return response.data;
};

export const updateManagedDevice = async (
  deviceId: number,
  payload: ManagedDeviceUpdatePayload,
): Promise<ManagedDevice> => {
  const response = await apiClient.put<ManagedDevice>(`/api/v1/management/managed/${deviceId}`, payload);
  return response.data;
};

export const deleteManagedDevice = async (deviceId: number): Promise<void> => {
  await apiClient.delete(`/api/v1/management/managed/${deviceId}`);
};

export const fetchAvailableChannels = async (): Promise<ChannelOption[]> => {
  const response = await apiClient.get<ChannelOption[]>('/api/v1/management/available-channels');
  return response.data;
};

export const sendDiagnosticSignal = async (hostname: string, port: number = 0, code: number = 1): Promise<void> => {
  await apiClient.post(`/api/v1/devices/${hostname}/command`, {
    command: 'diagnostic_signal',
    box: port,
    digit: code
  });
};

export interface BulkCommandTarget {
  hostname: string;
  port: number;
}

export interface BulkCommandRequest {
  targets: BulkCommandTarget[];
  command: string;
  channel?: string;
  digit?: number;
  priority?: number;
}

export interface BulkCommandResponse {
  success: boolean;
  batch_id: string;
  queued_count: number;
  command_ids: number[];
}

export const sendBulkCommand = async (request: BulkCommandRequest): Promise<BulkCommandResponse> => {
  const response = await apiClient.post<BulkCommandResponse>('/api/v1/commands/bulk', request);
  return response.data;
};
