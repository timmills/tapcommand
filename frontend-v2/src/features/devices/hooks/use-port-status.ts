import { useQuery } from '@tanstack/react-query';
import { apiClient } from '@/lib/axios';

interface PortStatus {
  port: number;
  last_channel: string | null;
  last_command: string | null;
  last_command_at: string | null;
  last_power_state: 'on' | 'off' | null;
  last_power_command_at: string | null;
  updated_at: string | null;
}

interface PortStatusResponse {
  hostname: string;
  port_statuses: PortStatus[];
}

export function usePortStatus(hostname: string | undefined) {
  return useQuery({
    queryKey: ['port-status', hostname],
    queryFn: async (): Promise<PortStatusResponse | null> => {
      if (!hostname) return null;

      const response = await apiClient.get<PortStatusResponse>(`/api/v1/commands/${hostname}/port-status`);
      return response.data;
    },
    enabled: !!hostname,
    staleTime: 30000, // 30 seconds
    refetchInterval: 60000, // Refetch every minute
  });
}

export function getLastChannelForPort(
  portStatusResponse: PortStatusResponse | null | undefined,
  port: number
): string | null {
  if (!portStatusResponse) return null;

  const portStatus = portStatusResponse.port_statuses.find((ps) => ps.port === port);
  return portStatus?.last_channel || null;
}

export function getPowerStateForPort(
  portStatusResponse: PortStatusResponse | null | undefined,
  port: number
): 'on' | 'off' | null {
  if (!portStatusResponse) return null;

  const portStatus = portStatusResponse.port_statuses.find((ps) => ps.port === port);
  return portStatus?.last_power_state || null;
}
