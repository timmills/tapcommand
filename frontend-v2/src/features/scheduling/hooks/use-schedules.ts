/**
 * React Query hooks for schedules
 */

import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import {
  fetchSchedules,
  fetchUpcomingSchedules,
  fetchSchedule,
  createSchedule,
  updateSchedule,
  deleteSchedule,
  toggleSchedule,
  runScheduleNow,
  fetchScheduleHistory,
  type ListSchedulesParams,
} from '../api/schedules-api';
import type { CreateScheduleRequest, UpdateScheduleRequest } from '../types/schedule';

// Query keys
export const schedulesKeys = {
  all: ['schedules'] as const,
  lists: () => [...schedulesKeys.all, 'list'] as const,
  list: (params: ListSchedulesParams) => [...schedulesKeys.lists(), params] as const,
  upcoming: (limit?: number) => [...schedulesKeys.all, 'upcoming', limit] as const,
  details: () => [...schedulesKeys.all, 'detail'] as const,
  detail: (id: number) => [...schedulesKeys.details(), id] as const,
  history: (id: number, limit?: number, offset?: number) =>
    [...schedulesKeys.detail(id), 'history', limit, offset] as const,
};

/**
 * Hook to fetch all schedules
 */
export function useSchedules(params: ListSchedulesParams = {}) {
  return useQuery({
    queryKey: schedulesKeys.list(params),
    queryFn: () => fetchSchedules(params),
    staleTime: 30_000, // 30 seconds
  });
}

/**
 * Hook to fetch upcoming schedules
 */
export function useUpcomingSchedules(limit: number = 5) {
  return useQuery({
    queryKey: schedulesKeys.upcoming(limit),
    queryFn: () => fetchUpcomingSchedules(limit),
    refetchInterval: 60_000, // Refetch every 60 seconds
    staleTime: 30_000,
  });
}

/**
 * Hook to fetch a single schedule
 */
export function useSchedule(id: number) {
  return useQuery({
    queryKey: schedulesKeys.detail(id),
    queryFn: () => fetchSchedule(id),
    enabled: !!id,
  });
}

/**
 * Hook to fetch schedule execution history
 */
export function useScheduleHistory(id: number, limit: number = 10, offset: number = 0) {
  return useQuery({
    queryKey: schedulesKeys.history(id, limit, offset),
    queryFn: () => fetchScheduleHistory(id, limit, offset),
    enabled: !!id,
  });
}

/**
 * Hook to create a schedule
 */
export function useCreateSchedule() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (data: CreateScheduleRequest) => createSchedule(data),
    onSuccess: () => {
      // Invalidate all schedule lists
      queryClient.invalidateQueries({ queryKey: schedulesKeys.lists() });
      queryClient.invalidateQueries({ queryKey: schedulesKeys.upcoming() });
    },
  });
}

/**
 * Hook to update a schedule
 */
export function useUpdateSchedule() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: ({ id, data }: { id: number; data: UpdateScheduleRequest }) => updateSchedule(id, data),
    onSuccess: (_, variables) => {
      // Invalidate specific schedule and lists
      queryClient.invalidateQueries({ queryKey: schedulesKeys.detail(variables.id) });
      queryClient.invalidateQueries({ queryKey: schedulesKeys.lists() });
      queryClient.invalidateQueries({ queryKey: schedulesKeys.upcoming() });
    },
  });
}

/**
 * Hook to delete a schedule
 */
export function useDeleteSchedule() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (id: number) => deleteSchedule(id),
    onSuccess: () => {
      // Invalidate all schedule lists
      queryClient.invalidateQueries({ queryKey: schedulesKeys.lists() });
      queryClient.invalidateQueries({ queryKey: schedulesKeys.upcoming() });
    },
  });
}

/**
 * Hook to toggle schedule active status
 */
export function useToggleSchedule() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (id: number) => toggleSchedule(id),
    onSuccess: (data) => {
      // Update specific schedule and invalidate lists
      queryClient.setQueryData(schedulesKeys.detail(data.id), data);
      queryClient.invalidateQueries({ queryKey: schedulesKeys.lists() });
      queryClient.invalidateQueries({ queryKey: schedulesKeys.upcoming() });
    },
  });
}

/**
 * Hook to run a schedule manually
 */
export function useRunScheduleNow() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (id: number) => runScheduleNow(id),
    onSuccess: (_, id) => {
      // Invalidate history for this schedule
      queryClient.invalidateQueries({ queryKey: schedulesKeys.detail(id) });
      queryClient.invalidateQueries({ queryKey: [...schedulesKeys.detail(id), 'history'] });
    },
  });
}
