import { useState, useEffect, useCallback } from 'react';
import type { Device } from '../types';

const API_BASE_URL = 'http://localhost:8000';

export const useDevices = () => {
  const [devices, setDevices] = useState<Device[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const fetchDevices = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const response = await fetch(`${API_BASE_URL}/api/v1/management/managed`);
      if (!response.ok) {
        throw new Error(`Failed to fetch devices: ${response.statusText}`);
      }
      const data = await response.json();
      setDevices(data);
    } catch (err) {
      const errorMessage = err instanceof Error ? err.message : 'Failed to fetch devices';
      setError(errorMessage);
      console.error('Error fetching devices:', err);
    } finally {
      setLoading(false);
    }
  }, []);

  const refreshDevice = useCallback(async (deviceId: string) => {
    try {
      const response = await fetch(`${API_BASE_URL}/api/v1/management/managed/${deviceId}/health-check`, {
        method: 'POST',
      });
      if (!response.ok) {
        throw new Error(`Failed to refresh device: ${response.statusText}`);
      }
      await fetchDevices();
    } catch (err) {
      const errorMessage = err instanceof Error ? err.message : 'Failed to refresh device';
      setError(errorMessage);
      console.error('Error refreshing device:', err);
    }
  }, [fetchDevices]);

  const updateDevice = useCallback(async (deviceId: string, updates: Partial<Device>) => {
    try {
      // Device updates not directly supported - would need specific update endpoints
      throw new Error('Device updates not yet implemented');
      if (!response.ok) {
        throw new Error(`Failed to update device: ${response.statusText}`);
      }
      await fetchDevices();
    } catch (err) {
      const errorMessage = err instanceof Error ? err.message : 'Failed to update device';
      setError(errorMessage);
      console.error('Error updating device:', err);
    }
  }, [fetchDevices]);

  const deleteDevice = useCallback(async (deviceId: string) => {
    try {
      const response = await fetch(`${API_BASE_URL}/api/v1/management/managed/${deviceId}`, {
        method: 'DELETE',
      });
      if (!response.ok) {
        throw new Error(`Failed to delete device: ${response.statusText}`);
      }
      await fetchDevices();
    } catch (err) {
      const errorMessage = err instanceof Error ? err.message : 'Failed to delete device';
      setError(errorMessage);
      console.error('Error deleting device:', err);
    }
  }, [fetchDevices]);

  useEffect(() => {
    fetchDevices();
  }, [fetchDevices]);

  return {
    devices,
    loading,
    error,
    fetchDevices,
    refreshDevice,
    updateDevice,
    deleteDevice,
  };
};