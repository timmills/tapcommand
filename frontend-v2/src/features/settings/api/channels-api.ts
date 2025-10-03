import { apiClient } from '@/lib/axios';
import type {
  ChannelGroupsResponse,
  ChannelLocationListResponse,
  ChannelVisibilityUpdatePayload,
} from '@/types';

export const fetchChannelLocations = async (): Promise<ChannelLocationListResponse> => {
  const response = await apiClient.get<ChannelLocationListResponse>('/api/v1/settings/channel-locations');
  return response.data;
};

export const selectChannelLocation = async (availability: string): Promise<ChannelLocationListResponse> => {
  const response = await apiClient.post<ChannelLocationListResponse>('/api/v1/settings/channel-locations/select', {
    availability,
  });
  return response.data;
};

export const fetchChannelsForLocation = async (availability?: string): Promise<ChannelGroupsResponse> => {
  const response = await apiClient.get<ChannelGroupsResponse>('/api/v1/settings/channels', {
    params: availability ? { availability } : undefined,
  });
  return response.data;
};

export const updateChannelVisibility = async (
  payload: ChannelVisibilityUpdatePayload,
): Promise<{ enabled: number; disabled: number }> => {
  const response = await apiClient.patch<{ enabled: number; disabled: number }>(
    '/api/v1/settings/channels',
    payload,
  );
  return response.data;
};
