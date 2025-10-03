import { useQuery } from '@tanstack/react-query';
import { apiClient } from '@/lib/axios';

interface QueueMetrics {
  pending: number;
  processing: number;
  failed: number;
  completed_last_hour: number;
  avg_execution_time_ms: number | null;
  oldest_pending_age_seconds: number | null;
}

export function useQueueMetrics() {
  return useQuery({
    queryKey: ['queue-metrics'],
    queryFn: async (): Promise<QueueMetrics> => {
      const response = await apiClient.get<QueueMetrics>('/api/v1/commands/queue/metrics');
      return response.data;
    },
    refetchInterval: 3000, // Refetch every 3 seconds for real-time updates
    staleTime: 1000, // Consider data stale after 1 second
  });
}
