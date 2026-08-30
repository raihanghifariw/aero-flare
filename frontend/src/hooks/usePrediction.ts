import useSWR from 'swr';
import { apiFetch } from '@/lib/api';
import type { Prediction } from '@/types/prediction';

/**
 * SWR hook for a fire spread prediction by event ID.
 * Returns null data when event_id is falsy.
 */
export function usePrediction(event_id: string | null) {
  const key = event_id ? `/predictions/${event_id}` : null;

  return useSWR<Prediction | null>(key, apiFetch, {
    revalidateOnFocus: false,
    shouldRetryOnError: false,
  });
}

