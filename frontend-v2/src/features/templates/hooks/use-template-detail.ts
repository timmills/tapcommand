import { useQuery } from '@tanstack/react-query';
import { fetchTemplateDetail } from '../api/templates-api';

export const useTemplateDetail = (templateId: number | null) =>
  useQuery({
    queryKey: ['templates', 'detail', templateId],
    queryFn: () => {
      if (!templateId) throw new Error('Template id is required');
      return fetchTemplateDetail(templateId);
    },
    enabled: templateId !== null,
  });
