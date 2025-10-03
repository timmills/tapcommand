/**
 * Schedules API Client
 */

import type {
  Schedule,
  ScheduleExecution,
  CreateScheduleRequest,
  UpdateScheduleRequest,
  RunNowResponse,
} from '../types/schedule';

const API_BASE = '/api/v1/schedules';

export interface ListSchedulesParams {
  active_only?: boolean;
  limit?: number;
  offset?: number;
}

export interface ListSchedulesResponse {
  schedules: Schedule[];
  total: number;
}

/**
 * Fetch all schedules
 */
export async function fetchSchedules(params: ListSchedulesParams = {}): Promise<ListSchedulesResponse> {
  const searchParams = new URLSearchParams();
  if (params.active_only) searchParams.append('active_only', 'true');
  if (params.limit) searchParams.append('limit', params.limit.toString());
  if (params.offset) searchParams.append('offset', params.offset.toString());

  const url = `${API_BASE}${searchParams.toString() ? `?${searchParams}` : ''}`;
  const response = await fetch(url);

  if (!response.ok) {
    throw new Error(`Failed to fetch schedules: ${response.statusText}`);
  }

  return response.json();
}

/**
 * Fetch upcoming schedules
 */
export async function fetchUpcomingSchedules(limit: number = 5): Promise<Schedule[]> {
  const response = await fetch(`${API_BASE}/upcoming?limit=${limit}`);

  if (!response.ok) {
    throw new Error(`Failed to fetch upcoming schedules: ${response.statusText}`);
  }

  return response.json();
}

/**
 * Fetch a single schedule by ID
 */
export async function fetchSchedule(id: number): Promise<Schedule> {
  const response = await fetch(`${API_BASE}/${id}`);

  if (!response.ok) {
    throw new Error(`Failed to fetch schedule: ${response.statusText}`);
  }

  return response.json();
}

/**
 * Create a new schedule
 */
export async function createSchedule(data: CreateScheduleRequest): Promise<Schedule> {
  const response = await fetch(API_BASE, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
    },
    body: JSON.stringify(data),
  });

  if (!response.ok) {
    const error = await response.json().catch(() => ({ detail: response.statusText }));
    throw new Error(error.detail || 'Failed to create schedule');
  }

  return response.json();
}

/**
 * Update an existing schedule
 */
export async function updateSchedule(id: number, data: UpdateScheduleRequest): Promise<Schedule> {
  const response = await fetch(`${API_BASE}/${id}`, {
    method: 'PUT',
    headers: {
      'Content-Type': 'application/json',
    },
    body: JSON.stringify(data),
  });

  if (!response.ok) {
    const error = await response.json().catch(() => ({ detail: response.statusText }));
    throw new Error(error.detail || 'Failed to update schedule');
  }

  return response.json();
}

/**
 * Delete a schedule
 */
export async function deleteSchedule(id: number): Promise<void> {
  const response = await fetch(`${API_BASE}/${id}`, {
    method: 'DELETE',
  });

  if (!response.ok) {
    throw new Error(`Failed to delete schedule: ${response.statusText}`);
  }
}

/**
 * Toggle schedule active status
 */
export async function toggleSchedule(id: number): Promise<Schedule> {
  const response = await fetch(`${API_BASE}/${id}/toggle`, {
    method: 'PATCH',
  });

  if (!response.ok) {
    throw new Error(`Failed to toggle schedule: ${response.statusText}`);
  }

  return response.json();
}

/**
 * Manually run a schedule now
 */
export async function runScheduleNow(id: number): Promise<RunNowResponse> {
  const response = await fetch(`${API_BASE}/${id}/run`, {
    method: 'POST',
  });

  if (!response.ok) {
    const error = await response.json().catch(() => ({ detail: response.statusText }));
    throw new Error(error.detail || 'Failed to run schedule');
  }

  return response.json();
}

/**
 * Fetch execution history for a schedule
 */
export async function fetchScheduleHistory(
  id: number,
  limit: number = 10,
  offset: number = 0
): Promise<ScheduleExecution[]> {
  const response = await fetch(`${API_BASE}/${id}/history?limit=${limit}&offset=${offset}`);

  if (!response.ok) {
    throw new Error(`Failed to fetch schedule history: ${response.statusText}`);
  }

  return response.json();
}
