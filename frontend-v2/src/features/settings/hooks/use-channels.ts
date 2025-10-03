import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import type { ChannelGroupsResponse, ChannelLocationListResponse } from '@/types';
import {
  fetchChannelLocations,
  fetchChannelsForLocation,
  selectChannelLocation,
  updateChannelVisibility,
} from '../api/channels-api';
import type { ChannelVisibilityUpdatePayload } from '@/types';

export const useChannelLocations = () => {
  return useQuery<ChannelLocationListResponse, Error>({
    queryKey: ['channel-locations'],
    queryFn: fetchChannelLocations,
    staleTime: 5 * 60 * 1000,
  });
};

export const useSelectChannelLocation = () => {
  const queryClient = useQueryClient();
  return useMutation<ChannelLocationListResponse, Error, string>({
    mutationFn: (availability) => selectChannelLocation(availability),
    onSuccess: (data) => {
      queryClient.setQueryData(['channel-locations'], data);
      queryClient.invalidateQueries({ queryKey: ['channel-groups'] });
    },
  });
};

export const useChannelGroups = (availability?: string) => {
  return useQuery<ChannelGroupsResponse, Error>({
    queryKey: ['channel-groups', availability ?? 'selected'],
    queryFn: () => fetchChannelsForLocation(availability),
  });
};

export const useUpdateChannelVisibility = () => {
  const queryClient = useQueryClient();
  return useMutation<{ enabled: number; disabled: number }, Error, ChannelVisibilityUpdatePayload>({
    mutationFn: (payload) => updateChannelVisibility(payload),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['channel-groups'] });
      queryClient.invalidateQueries({ queryKey: ['channel-locations'] });
    },
  });
};
