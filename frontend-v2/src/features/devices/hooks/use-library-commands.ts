import { useQuery } from '@tanstack/react-query';
import { apiClient } from '@/lib/axios';

interface IRCommand {
  id: number;
  name: string;
  display_name: string | null;
  category: string | null;
  protocol: string;
  signal_data: Record<string, any>;
}

interface LibraryCommandsResponse {
  library: {
    id: number;
    name: string;
    brand: string | null;
    model: string | null;
  };
  commands: IRCommand[];
}

export const useLibraryCommands = (libraryId: number | null | undefined) => {
  return useQuery({
    queryKey: ['library-commands', libraryId],
    queryFn: async (): Promise<LibraryCommandsResponse> => {
      if (!libraryId) {
        throw new Error('Library ID is required');
      }
      const response = await apiClient.get<LibraryCommandsResponse>(
        `/api/v1/ir-codes/libraries/${libraryId}/commands`
      );
      return response.data;
    },
    enabled: !!libraryId,
    staleTime: 5 * 60 * 1000, // 5 minutes
  });
};
