import { useQuery } from '@tanstack/react-query';
import { fetchTemplateHierarchy } from '../api/templates-api';

export const useTemplateHierarchy = () =>
  useQuery({
    queryKey: ['template-hierarchy'],
    queryFn: fetchTemplateHierarchy,
    staleTime: 5 * 60_000,
  });
