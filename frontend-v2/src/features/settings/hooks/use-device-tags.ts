import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import type { DeviceTag } from '@/types';
import {
  createDeviceTag,
  deleteDeviceTag,
  fetchDeviceTags,
  updateDeviceTag,
  type DeviceTagPayload,
} from '../api/device-tags-api';

export const useDeviceTags = () => {
  return useQuery<DeviceTag[], Error>({
    queryKey: ['device-tags'],
    queryFn: fetchDeviceTags,
  });
};

export const useCreateDeviceTag = () => {
  const queryClient = useQueryClient();
  return useMutation<DeviceTag, Error, DeviceTagPayload>({
    mutationFn: (payload) => createDeviceTag(payload),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['device-tags'] });
    },
  });
};

export const useUpdateDeviceTag = () => {
  const queryClient = useQueryClient();
  return useMutation<DeviceTag, Error, { id: number; payload: DeviceTagPayload }>({
    mutationFn: ({ id, payload }) => updateDeviceTag(id, payload),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['device-tags'] });
    },
  });
};

export const useDeleteDeviceTag = () => {
  const queryClient = useQueryClient();
  return useMutation<void, Error, number>({
    mutationFn: (id) => deleteDeviceTag(id),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['device-tags'] });
    },
  });
};
