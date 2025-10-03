import { useMutation, useQueryClient } from '@tanstack/react-query';
import { updateManagedDevice, type ManagedDeviceUpdatePayload } from '../api/devices-api';
import type { ManagedDevice } from '@/types';

interface UpdateArgs {
  deviceId: number;
  payload: ManagedDeviceUpdatePayload;
}

export const useUpdateManagedDevice = () => {
  const queryClient = useQueryClient();

  return useMutation<ManagedDevice, Error, UpdateArgs>({
    mutationFn: ({ deviceId, payload }) => updateManagedDevice(deviceId, payload),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['managed-devices'] });
      queryClient.invalidateQueries({ queryKey: ['device-tags'] });
    },
  });
};
