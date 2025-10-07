import { useQuery } from '@tanstack/react-query';
import axios from 'axios';

interface VirtualDevice {
  id: number;
  controller_id: number;
  port_number: number;
  port_id: string | null;
  device_name: string;
  device_type: string | null;
  ip_address: string;
  mac_address: string | null;
  port: number | null;
  protocol: string | null;
  is_active: boolean;
  is_online: boolean;
  fallback_ir_controller: string | null;
  fallback_ir_port: number | null;
  power_on_method: string | null;
  control_strategy: string | null;
}

async function fetchVirtualDevices(): Promise<VirtualDevice[]> {
  const response = await axios.get('http://localhost:8000/api/virtual-controllers/devices/all');
  return response.data;
}

export function useVirtualDevices() {
  return useQuery({
    queryKey: ['virtualDevices'],
    queryFn: fetchVirtualDevices,
    refetchInterval: 5000, // Refetch every 5 seconds like managed devices
  });
}
