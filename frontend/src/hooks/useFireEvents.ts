import useSWR from 'swr';
import { apiFetch } from '@/lib/api';
import { EVENTS_POLL_INTERVAL_MS } from '@/lib/constants';
import type { FireEventsResponse, FireStatus } from '@/types/fire-event';

export interface UseFireEventsParams {
  page?: number;
  limit?: number;
  status?: FireStatus | '';
  danger_level_min?: number;
}

/**
 * SWR hook for the fire events list.
 * Polls every 5 minutes per plan/frontend_agent.md.
 * All params are included in the SWR key for correct cache invalidation.
 */
export function useFireEvents(params: UseFireEventsParams = {}) {
  const { page = 1, limit = 50, status = '', danger_level_min } = params;

  const qs = new URLSearchParams({
    page: String(page),
    limit: String(limit),
    ...(status && { status }),
    ...(danger_level_min !== undefined && { danger_level_min: String(danger_level_min) }),
  });

  const key = `/events?${qs.toString()}`;

  return useSWR<FireEventsResponse>(key, apiFetch, {
    refreshInterval: EVENTS_POLL_INTERVAL_MS,
    revalidateOnFocus: false,
  });
}
