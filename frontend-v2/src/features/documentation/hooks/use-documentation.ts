import { useQuery } from '@tanstack/react-query';
import { documentationApi } from '../api/documentation-api';

export function useDocumentationFiles() {
  return useQuery({
    queryKey: ['documentation', 'files'],
    queryFn: documentationApi.listFiles,
  });
}

export function useDocumentationContent(filePath: string | null) {
  return useQuery({
    queryKey: ['documentation', 'content', filePath],
    queryFn: () => documentationApi.getContent(filePath!),
    enabled: !!filePath,
  });
}
