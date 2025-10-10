import { useMutation, useQueryClient } from '@tanstack/react-query';
import { updateApplicationSetting } from '../api/application-settings-api';
import type { ApplicationSettingUpdateRequest } from '../api/application-settings-api';

export const useUpdateApplicationSetting = () => {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (request: ApplicationSettingUpdateRequest) => updateApplicationSetting(request),
    onSuccess: () => {
      // Invalidate both public and private settings queries
      queryClient.invalidateQueries({ queryKey: ['application-settings'] });
    },
  });
};
