import { apiClient } from '@/lib/axios';

export interface ApplicationSettingValue {
  value: unknown;
  description?: string | null;
  setting_type?: string;
  is_public?: boolean;
  updated_at?: string;
}

export type ApplicationSettingsMap = Record<string, ApplicationSettingValue>;

export interface ApplicationSettingUpdateRequest {
  key: string;
  value: unknown;
  description?: string;
  setting_type?: string;
  is_public?: boolean;
}

export const fetchApplicationSettings = async (includePrivate = false): Promise<ApplicationSettingsMap> => {
  const response = await apiClient.get<ApplicationSettingsMap>('/api/v1/settings/app', {
    params: { include_private: includePrivate },
  });
  return response.data;
};

export const updateApplicationSetting = async (request: ApplicationSettingUpdateRequest): Promise<void> => {
  await apiClient.put(`/api/v1/settings/app/${request.key}`, request);
};
