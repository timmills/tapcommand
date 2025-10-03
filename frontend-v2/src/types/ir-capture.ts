/**
 * TypeScript types for IR Remote Code Capture System
 */

export interface CaptureSession {
  id: number;
  session_name: string;
  device_type: string;
  brand: string | null;
  model: string | null;
  status: 'active' | 'completed' | 'cancelled';
  code_count: number;
  created_at: string;
}

export interface CreateSessionRequest {
  session_name: string;
  device_type?: string;
  brand?: string;
  model?: string;
  notes?: string;
}

export interface CapturedCode {
  id: number;
  button_name: string;
  button_category: string | null;
  protocol: string;
  has_raw_data: boolean;
  capture_timestamp: string;
}

export interface AddCodeRequest {
  button_name: string;
  button_category?: string;
  protocol?: string;
  raw_data: string;
  decoded_address?: string;
  decoded_command?: string;
  decoded_data?: string;
}

export interface CapturedRemote {
  id: number;
  name: string;
  device_type: string;
  brand: string | null;
  model: string | null;
  button_count: number;
  is_favorite: boolean;
  created_at: string;
}

export interface CreateRemoteRequest {
  session_id: number;
  name: string;
  description?: string;
  is_favorite?: boolean;
}

export interface RemoteDetail {
  id: number;
  name: string;
  device_type: string;
  brand: string | null;
  model: string | null;
  description: string | null;
  button_count: number;
  is_favorite: boolean;
  buttons: RemoteButton[];
  created_at: string;
}

export interface RemoteButton {
  button_name: string;
  button_label: string;
  button_category: string | null;
  protocol: string;
  has_raw_data: boolean;
}
