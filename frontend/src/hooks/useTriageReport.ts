import useSWR from 'swr';
import { apiFetch } from '@/lib/api';
import type { TriageReport } from '@/types/triage-report';

/**
 * SWR hook for a single triage report by event ID.
 * Returns null data when event_id is falsy (modal closed).
 */
export function useTriageReport(event_id: string | null) {
  const key = event_id ? `/triage/${event_id}` : null;

  return useSWR<TriageReport>(key, apiFetch, {
    revalidateOnFocus: false,
    // No polling — triage reports are immutable once written
  });
}
