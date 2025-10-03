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

// ==================== DEVICE INTEGRATION ====================

export interface DeviceStatus {
  online: boolean;
  ip_address: string;
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
