import { useState, useEffect, useCallback } from 'react';
import type { DeviceTag } from '../types';

const API_BASE_URL = 'http://localhost:8000';

export const useTags = () => {
  const [deviceTags, setDeviceTags] = useState<DeviceTag[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const fetchTags = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      // Mock tags data until backend API is implemented
      const mockTags: DeviceTag[] = [
        {
          id: 1,
          name: "Living Room",
          color: "#3b82f6",
          description: "Devices in the living room area",
          usage_count: 3,
          created_at: "2025-09-25T00:00:00Z",
          updated_at: "2025-09-25T00:00:00Z"
        },
        {
          id: 2,
          name: "Bedroom",
          color: "#10b981",
          description: "Bedroom entertainment devices",
          usage_count: 1,
          created_at: "2025-09-25T00:00:00Z",
          updated_at: "2025-09-25T00:00:00Z"
        }
      ];

      setDeviceTags(mockTags);
    } catch (err) {
      const errorMessage = err instanceof Error ? err.message : 'Failed to fetch tags';
      setError(errorMessage);
      console.error('Error fetching tags:', err);
    } finally {
      setLoading(false);
    }
  }, []);

  const createTag = useCallback(async (tagData: {
    name: string;
    color: string;
    description?: string;
  }) => {
    setError(null);
    try {
      // Mock create tag - add new tag to existing list
      const newTag: DeviceTag = {
        id: Date.now(), // Simple ID generation for mock
        name: tagData.name,
        color: tagData.color,
        description: tagData.description || '',
        usage_count: 0,
        created_at: new Date().toISOString(),
        updated_at: new Date().toISOString()
      };

      setDeviceTags(prevTags => [...prevTags, newTag]);
    } catch (err) {
      const errorMessage = err instanceof Error ? err.message : 'Failed to create tag';
      setError(errorMessage);
      console.error('Error creating tag:', err);
      throw err;
    }
  }, []);

  const updateTag = useCallback(async (tagId: number, tagData: {
    name: string;
    color: string;
    description?: string;
  }) => {
    setError(null);
    try {
      // Mock update tag - update existing tag in list
      setDeviceTags(prevTags =>
        prevTags.map(tag =>
          tag.id === tagId
            ? {
                ...tag,
                name: tagData.name,
                color: tagData.color,
                description: tagData.description || '',
                updated_at: new Date().toISOString()
              }
            : tag
        )
      );
    } catch (err) {
      const errorMessage = err instanceof Error ? err.message : 'Failed to update tag';
      setError(errorMessage);
      console.error('Error updating tag:', err);
      throw err;
    }
  }, []);

  const deleteTag = useCallback(async (tagId: number) => {
    setError(null);
    try {
      // Mock delete tag - remove tag from list
      setDeviceTags(prevTags => prevTags.filter(tag => tag.id !== tagId));
    } catch (err) {
      const errorMessage = err instanceof Error ? err.message : 'Failed to delete tag';
      setError(errorMessage);
      console.error('Error deleting tag:', err);
    }
  }, []);

  useEffect(() => {
    fetchTags();
  }, [fetchTags]);

  return {
    deviceTags,
    loading,
    error,
    fetchTags,
    createTag,
    updateTag,
    deleteTag,
  };
};