import { apiClient } from '@/lib/axios';

export interface DocumentationFile {
  filename: string;
  path: string;
  title: string;
  category: string;
  size: number;
  modified: number;
}

export interface DocumentationContent {
  filename: string;
  path: string;
  content: string;
  size: number;
  modified: number;
}

export const documentationApi = {
  // List all documentation files
  listFiles: async (): Promise<DocumentationFile[]> => {
    const response = await apiClient.get('/api/documentation/list');
    return response.data;
  },

  // Get content of a specific documentation file
  getContent: async (filePath: string): Promise<DocumentationContent> => {
    const response = await apiClient.get(`/api/documentation/content/${filePath}`);
    return response.data;
  },
};
