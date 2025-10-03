import { useMutation, useQueryClient } from '@tanstack/react-query';
import { connectDiscoveredDevice } from '../api/discovery-api';

interface ConnectArgs {
  hostname: string;
  payload?: Record<string, unknown>;
}

export const useConnectDiscoveredDevice = () => {
  const queryClient = useQueryClient();

  return useMutation<void, Error, ConnectArgs>({
    mutationFn: ({ hostname, payload }) => connectDiscoveredDevice(hostname, payload ?? {}),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['discovery', 'devices'] });
      queryClient.invalidateQueries({ queryKey: ['managed-devices'] });
      queryClient.invalidateQueries({ queryKey: ['device-tags'] });
    },
  });
};
