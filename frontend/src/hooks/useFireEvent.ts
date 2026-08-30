import useSWR from 'swr';
import { apiFetch } from '@/lib/api';
import type { FireEvent } from '@/types/fire-event';

export function useFireEvent(eventId: string | null) {
  const key = eventId ? `/events/${eventId}` : null;
  return useSWR<FireEvent>(key, apiFetch, {
    revalidateOnFocus: false,
    shouldRetryOnError: false,
  });
}

