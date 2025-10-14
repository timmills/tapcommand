import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { audioApi } from '../api/audio-api';
import { toast } from 'sonner';

const QUERY_KEYS = {
  controllers: ['audio', 'controllers'] as const,
  zones: (controllerId?: string) => ['audio', 'zones', controllerId] as const,
  presets: (controllerId: string) => ['audio', 'presets', controllerId] as const,
  discoveredDevices: ['audio', 'discovered-devices'] as const,
};

// Fetch all audio controllers
export function useAudioControllers(refetchInterval: number = 5000) {
  return useQuery({
    queryKey: QUERY_KEYS.controllers,
    queryFn: audioApi.getControllers,
    refetchInterval, // Customizable polling interval (default 5 seconds)
  });
}

// Fetch all zones
export function useAudioZones(controllerId?: string) {
  return useQuery({
    queryKey: QUERY_KEYS.zones(controllerId),
    queryFn: () => audioApi.getZones(controllerId),
    refetchInterval: 5000,
  });
}

// Set volume
export function useSetVolume() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: ({ zoneId, volume }: { zoneId: number; volume: number }) =>
      audioApi.setVolume(zoneId, volume),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: QUERY_KEYS.controllers });
      queryClient.invalidateQueries({ queryKey: ['audio', 'zones'] });
    },
    onError: (error) => {
      toast.error('Failed to set volume', {
        description: error instanceof Error ? error.message : 'Unknown error',
      });
    },
  });
}

// Volume up
export function useVolumeUp() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (zoneId: number) => audioApi.volumeUp(zoneId),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: QUERY_KEYS.controllers });
      queryClient.invalidateQueries({ queryKey: ['audio', 'zones'] });
    },
    onError: (error) => {
      toast.error('Failed to increase volume', {
        description: error instanceof Error ? error.message : 'Unknown error',
      });
    },
  });
}

// Volume down
export function useVolumeDown() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (zoneId: number) => audioApi.volumeDown(zoneId),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: QUERY_KEYS.controllers });
      queryClient.invalidateQueries({ queryKey: ['audio', 'zones'] });
    },
    onError: (error) => {
      toast.error('Failed to decrease volume', {
        description: error instanceof Error ? error.message : 'Unknown error',
      });
    },
  });
}

// Toggle mute
export function useToggleMute() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (zoneId: number) => audioApi.toggleMute(zoneId),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: QUERY_KEYS.controllers });
      queryClient.invalidateQueries({ queryKey: ['audio', 'zones'] });
    },
    onError: (error) => {
      toast.error('Failed to toggle mute', {
        description: error instanceof Error ? error.message : 'Unknown error',
      });
    },
  });
}

// Delete controller
export function useDeleteController() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (controllerId: string) => audioApi.deleteController(controllerId),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: QUERY_KEYS.controllers });
      toast.success('Audio controller deleted');
    },
    onError: (error) => {
      toast.error('Failed to delete controller', {
        description: error instanceof Error ? error.message : 'Unknown error',
      });
    },
  });
}

// Rediscover zones
export function useRediscoverZones() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (controllerId: string) => audioApi.rediscoverZones(controllerId),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: QUERY_KEYS.controllers });
      toast.success('Zones rediscovered successfully');
    },
    onError: (error) => {
      toast.error('Failed to rediscover zones', {
        description: error instanceof Error ? error.message : 'Unknown error',
      });
    },
  });
}

// Add controller manually
export function useAddController() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (data: {
      ip_address: string;
      controller_name: string;
      port?: number;
      venue_name?: string;
      location?: string;
    }) => audioApi.addController(data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: QUERY_KEYS.controllers });
      toast.success('Audio controller added successfully');
    },
    onError: (error) => {
      toast.error('Failed to add controller', {
        description: error instanceof Error ? error.message : 'Unknown error',
      });
    },
  });
}

// Fetch presets for a controller
export function usePresets(controllerId: string) {
  return useQuery({
    queryKey: QUERY_KEYS.presets(controllerId),
    queryFn: () => audioApi.getPresets(controllerId),
    enabled: !!controllerId,
  });
}

// Recall a preset
export function useRecallPreset() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: ({ controllerId, presetNumber }: { controllerId: string; presetNumber: number }) =>
      audioApi.recallPreset(controllerId, presetNumber),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: QUERY_KEYS.controllers });
      queryClient.invalidateQueries({ queryKey: ['audio', 'zones'] });
      toast.success('Preset recalled successfully');
    },
    onError: (error) => {
      toast.error('Failed to recall preset', {
        description: error instanceof Error ? error.message : 'Unknown error',
      });
    },
  });
}

// Master volume control (all zones)
export function useSetMasterVolume() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: ({ controllerId, volume }: { controllerId: string; volume: number }) =>
      audioApi.setMasterVolume(controllerId, volume),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: QUERY_KEYS.controllers });
      queryClient.invalidateQueries({ queryKey: ['audio', 'zones'] });
    },
    onError: (error) => {
      toast.error('Failed to set master volume', {
        description: error instanceof Error ? error.message : 'Unknown error',
      });
    },
  });
}

export function useMasterVolumeUp() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (controllerId: string) => audioApi.masterVolumeUp(controllerId),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: QUERY_KEYS.controllers });
      queryClient.invalidateQueries({ queryKey: ['audio', 'zones'] });
    },
    onError: (error) => {
      toast.error('Failed to increase master volume', {
        description: error instanceof Error ? error.message : 'Unknown error',
      });
    },
  });
}

export function useMasterVolumeDown() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (controllerId: string) => audioApi.masterVolumeDown(controllerId),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: QUERY_KEYS.controllers });
      queryClient.invalidateQueries({ queryKey: ['audio', 'zones'] });
    },
    onError: (error) => {
      toast.error('Failed to decrease master volume', {
        description: error instanceof Error ? error.message : 'Unknown error',
      });
    },
  });
}

// Sync volumes from device (Plena Matrix only)
export function useSyncVolumes() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (controllerId: string) => audioApi.syncVolumes(controllerId),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: QUERY_KEYS.controllers });
      queryClient.invalidateQueries({ queryKey: ['audio', 'zones'] });
      toast.success('Volumes synced from device');
    },
    onError: (error) => {
      toast.error('Failed to sync volumes', {
        description: error instanceof Error ? error.message : 'Unknown error',
      });
    },
  });
}

// Get active preset (Plena Matrix only)
export function useActivePreset(controllerId: string, enabled: boolean = true) {
  return useQuery({
    queryKey: ['audio', 'active-preset', controllerId],
    queryFn: () => audioApi.getActivePreset(controllerId),
    enabled: enabled && !!controllerId,
    refetchInterval: 30000, // Refetch every 30 seconds
  });
}

// Fetch unadopted discovered audio devices
export function useDiscoveredAudioDevices() {
  return useQuery({
    queryKey: QUERY_KEYS.discoveredDevices,
    queryFn: audioApi.getDiscoveredDevices,
    refetchInterval: 10000, // Refetch every 10 seconds
  });
}
