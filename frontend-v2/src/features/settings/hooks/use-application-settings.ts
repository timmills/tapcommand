import { useQuery } from '@tanstack/react-query';
import { fetchApplicationSettings } from '../api/application-settings-api';

export const useApplicationSettings = (includePrivate = false) =>
  useQuery({
    queryKey: ['application-settings', includePrivate],
    queryFn: () => fetchApplicationSettings(includePrivate),
    staleTime: 60_000,
  });
