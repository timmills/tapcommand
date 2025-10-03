import { useQuery } from '@tanstack/react-query';
import { fetchManagedDevices } from '../api/devices-api';

export const useManagedDevices = () => {
  return useQuery({
    queryKey: ['managed-devices'],
    queryFn: fetchManagedDevices,
    staleTime: 30_000,
  });
};
