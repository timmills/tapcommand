import { useQuery } from '@tanstack/react-query';
import { fetchTemplateSummaries } from '../api/templates-api';

export const useTemplateSummaries = () =>
  useQuery({
    queryKey: ['templates', 'summaries'],
    queryFn: fetchTemplateSummaries,
    staleTime: 60_000,
  });
