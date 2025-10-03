import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import {
  fetchDiscoveredDevices,
  startDiscovery as startDiscoveryRequest,
  stopDiscovery as stopDiscoveryRequest,
} from '../api/discovery-api';

export const useDiscoveryDevices = () => {
  return useQuery({
    queryKey: ['discovery', 'devices'],
    queryFn: fetchDiscoveredDevices,
    refetchInterval: 10_000,
    select: (devices) => devices.filter((device) => !device.is_managed),
  });
};

export const useDiscoveryControls = () => {
  const queryClient = useQueryClient();

  const startDiscovery = useMutation({
    mutationFn: startDiscoveryRequest,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['discovery', 'devices'] });
    },
  });

  const stopDiscovery = useMutation({
    mutationFn: stopDiscoveryRequest,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['discovery', 'devices'] });
    },
  });

  return {
    startDiscovery,
    stopDiscovery,
  };
};
