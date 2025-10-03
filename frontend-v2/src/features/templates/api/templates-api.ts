import { API_BASE_URL } from '@/lib/env';
import { apiClient } from '@/lib/axios';
import type {
  TemplateDetail,
  TemplateSummary,
  TemplateCategory,
  TemplatePreviewRequest,
  TemplatePreviewResponse,
  FirmwareCompileResponse,
} from '@/types';

export const fetchTemplateSummaries = async (): Promise<TemplateSummary[]> => {
  const response = await apiClient.get<TemplateSummary[]>('/api/v1/templates');
  return response.data;
};

export const fetchTemplateDetail = async (templateId: number): Promise<TemplateDetail> => {
  const response = await apiClient.get<TemplateDetail>(`/api/v1/templates/${templateId}`);
  return response.data;
};

export const fetchTemplateHierarchy = async (): Promise<TemplateCategory[]> => {
  const response = await apiClient.get<TemplateCategory[]>('/api/v1/templates/device-hierarchy');
  return response.data;
};

export const generateTemplatePreview = async (
  payload: TemplatePreviewRequest,
): Promise<TemplatePreviewResponse> => {
  const response = await apiClient.post<TemplatePreviewResponse>('/api/v1/templates/preview', payload);
  return response.data;
};

export const compileTemplateFirmware = async (yaml: string): Promise<FirmwareCompileResponse> => {
  const response = await apiClient.post<FirmwareCompileResponse>(
    '/api/v1/templates/compile',
    { yaml },
    { timeout: 120_000 },
  );
  return response.data;
};

export const getFirmwareDownloadUrl = (filename: string) =>
  `${API_BASE_URL}/api/v1/templates/download/${encodeURIComponent(filename)}`;
