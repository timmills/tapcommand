import { useQuery } from '@tanstack/react-query';
import type { ChannelOption } from '@/types';
import { fetchAvailableChannels } from '../api/devices-api';

export const useAvailableChannels = () => {
  return useQuery<ChannelOption[], Error>({
    queryKey: ['available-channels'],
    queryFn: fetchAvailableChannels,
    staleTime: 5 * 60 * 1000,
  });
};
