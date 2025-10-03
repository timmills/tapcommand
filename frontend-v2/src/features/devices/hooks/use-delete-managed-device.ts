import { useMutation, useQueryClient } from '@tanstack/react-query';
import { deleteManagedDevice } from '../api/devices-api';

export const useDeleteManagedDevice = () => {
  const queryClient = useQueryClient();

  return useMutation<void, Error, number>({
    mutationFn: (deviceId) => deleteManagedDevice(deviceId),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['managed-devices'] });
      queryClient.invalidateQueries({ queryKey: ['device-tags'] });
    },
  });
};
