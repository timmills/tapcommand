import { useQuery, keepPreviousData } from '@tanstack/react-query';
import { generateTemplatePreview } from '../api/templates-api';
import type { TemplatePreviewAssignment, TemplatePreviewResponse } from '@/types';

export const useTemplatePreview = (
  templateId: number | null,
  assignments: TemplatePreviewAssignment[],
  includeComments: boolean,
) =>
  useQuery<TemplatePreviewResponse>({
    queryKey: ['template-preview', templateId, assignments, includeComments],
    queryFn: () => {
      if (!templateId) throw new Error('Template ID required for preview');
      return generateTemplatePreview({
        template_id: templateId,
        assignments,
        include_comments: includeComments,
      });
    },
    enabled: templateId !== null,
    placeholderData: keepPreviousData,
  });
