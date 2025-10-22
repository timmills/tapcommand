/**
 * API client for IR Remote Code Capture System
 */

import { apiClient } from '../../../lib/axios';
import type {
  CaptureSession,
  CreateSessionRequest,
  CapturedCode,
  AddCodeRequest,
  CapturedRemote,
  CreateRemoteRequest,
  RemoteDetail,
} from '../../../types/ir-capture';

const BASE_URL = '/api/v1/ir-capture';

// ==================== SESSIONS ====================

export const createCaptureSession = async (
  data: CreateSessionRequest
): Promise<CaptureSession> => {
  const response = await apiClient.post<CaptureSession>(`${BASE_URL}/sessions`, data);
  return response.data;
};

export const listCaptureSessions = async (
  status?: 'active' | 'completed' | 'cancelled'
): Promise<CaptureSession[]> => {
  const params = status ? { status } : {};
  const response = await apiClient.get<CaptureSession[]>(`${BASE_URL}/sessions`, { params });
  return response.data;
};

export const getCaptureSession = async (sessionId: number): Promise<CaptureSession> => {
  const response = await apiClient.get<CaptureSession>(`${BASE_URL}/sessions/${sessionId}`);
  return response.data;
};

export const completeSession = async (sessionId: number): Promise<void> => {
  await apiClient.post(`${BASE_URL}/sessions/${sessionId}/complete`);
};

// ==================== CODES ====================

export const addCodeToSession = async (
  sessionId: number,
  data: AddCodeRequest
): Promise<CapturedCode> => {
  const response = await apiClient.post<CapturedCode>(
    `${BASE_URL}/sessions/${sessionId}/codes`,
    data
  );
  return response.data;
};

export const listSessionCodes = async (sessionId: number): Promise<CapturedCode[]> => {
  const response = await apiClient.get<CapturedCode[]>(
    `${BASE_URL}/sessions/${sessionId}/codes`
  );
  return response.data;
};

export const deleteCode = async (sessionId: number, codeId: number): Promise<void> => {
  await apiClient.delete(`${BASE_URL}/sessions/${sessionId}/codes/${codeId}`);
};

// ==================== REMOTES ====================

export const createCapturedRemote = async (
  data: CreateRemoteRequest
): Promise<CapturedRemote> => {
  const response = await apiClient.post<CapturedRemote>(`${BASE_URL}/remotes`, data);
  return response.data;
};

export const listCapturedRemotes = async (
  deviceType?: string,
  favoritesOnly?: boolean
): Promise<CapturedRemote[]> => {
  const params: Record<string, string | boolean> = {};
  if (deviceType) params.device_type = deviceType;
  if (favoritesOnly) params.favorites_only = favoritesOnly;

  const response = await apiClient.get<CapturedRemote[]>(`${BASE_URL}/remotes`, { params });
  return response.data;
};

export const getRemoteDetail = async (remoteId: number): Promise<RemoteDetail> => {
  const response = await apiClient.get<RemoteDetail>(`${BASE_URL}/remotes/${remoteId}`);
  return response.data;
};

export const deleteRemote = async (remoteId: number): Promise<void> => {
  await apiClient.delete(`${BASE_URL}/remotes/${remoteId}`);
};

// ==================== DEVICE DISCOVERY ====================

export interface DiscoveredDevice {
  hostname: string;
  ip_address: string;
  port: number;
  mac_address: string;
  friendly_name: string;
  discovered_at: string;
}

export interface DiscoveredDevicesResponse {
  devices: DiscoveredDevice[];
  count: number;
}

export interface DeviceConfig {
  discovered_devices: Array<{
    hostname: string;
    ip_address: string;
    friendly_name: string;
  }>;
  manual_ip: string | null;
  using_auto_discovery: boolean;
  current_device?: {
    hostname: string;
    ip_address: string;
  };
}

export const getDiscoveredDevices = async (): Promise<DiscoveredDevicesResponse> => {
  const response = await apiClient.get<DiscoveredDevicesResponse>(`${BASE_URL}/devices/discovered`);
  return response.data;
};

export const getDeviceConfig = async (): Promise<DeviceConfig> => {
  const response = await apiClient.get<DeviceConfig>(`${BASE_URL}/device/config`);
  return response.data;
};

export const setManualIP = async (ip_address: string): Promise<{ success: boolean; message: string }> => {
  const response = await apiClient.post(`${BASE_URL}/device/set-ip`, { ip_address });
  return response.data;
};

export const clearManualIP = async (): Promise<{ success: boolean; message: string }> => {
  const response = await apiClient.delete(`${BASE_URL}/device/manual-ip`);
  return response.data;
};

// ==================== DEVICE INTEGRATION ====================

export interface DeviceStatus {
  online: boolean;
  ip_address: string;
  hostname?: string;
  wifi_signal?: { value: number; state: string };
  error?: string;
}

export interface LastCodeResponse {
  success: boolean;
  raw_data: string;
  timestamp: string;
}

export const getDeviceStatus = async (): Promise<DeviceStatus> => {
  const response = await apiClient.get<DeviceStatus>(`${BASE_URL}/device/status`);
  return response.data;
};

export const getLastCapturedCode = async (): Promise<LastCodeResponse> => {
  const response = await apiClient.get<LastCodeResponse>(`${BASE_URL}/device/last-code`);
  return response.data;
};

// ==================== FIRMWARE COMPILATION & DOWNLOAD ====================

export interface FirmwareConfig {
  filename: string;
  filepath: string;
  friendly_name: string;
  description: string;
}

export interface AvailableConfigsResponse {
  success: boolean;
  configs: FirmwareConfig[];
  count: number;
}

export interface SecretsResponse {
  success: boolean;
  message: string;
  path: string;
  preview: string;
}

export interface CompileResponse {
  success: boolean;
  message: string;
  binary_path?: string;
  file_size?: number;
  filename?: string;
  error?: string;
  stdout?: string;
}

export const getAvailableFirmwareConfigs = async (): Promise<AvailableConfigsResponse> => {
  const response = await apiClient.get<AvailableConfigsResponse>(`${BASE_URL}/firmware/available-configs`);
  return response.data;
};

export const generateSecrets = async (): Promise<SecretsResponse> => {
  const response = await apiClient.get<SecretsResponse>(`${BASE_URL}/firmware/generate-secrets`);
  return response.data;
};

export const compileFirmware = async (
  config_filename: string,
  clean_build: boolean = false
): Promise<CompileResponse> => {
  // Firmware compilation can take several minutes, so use extended timeout
  const response = await apiClient.post<CompileResponse>(
    `${BASE_URL}/firmware/compile`,
    {
      config_filename,
      clean_build
    },
    {
      timeout: 600000 // 10 minutes (matches backend timeout)
    }
  );
  return response.data;
};

export const downloadFirmware = (config_filename: string): string => {
  // Return download URL
  return `${apiClient.defaults.baseURL}${BASE_URL}/firmware/download/${config_filename}`;
};
