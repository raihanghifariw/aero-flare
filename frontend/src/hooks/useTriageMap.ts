import useSWR from 'swr';
import { apiFetch } from '@/lib/api';
import type { TriageReport } from '@/types/triage-report';

/**
 * Fetches triage reports for a list of event IDs in parallel via SWR.
 * Returns a lookup map: event_id → TriageReport.
 *
 * SWR deduplicates concurrent requests for the same key, so calling this
 * hook and useTriageReport(id) for the same id will share the same cache entry.
 */
export function useTriageMap(eventIds: string[]): Record<string, TriageReport> {
  // Build a stable key from sorted IDs so the hook re-runs when the list changes
  const key = eventIds.length > 0 ? eventIds.slice().sort().join(',') : null;

  const { data } = useSWR<Record<string, TriageReport>>(
    key ? `__triage_map__${key}` : null,
    async () => {
      const results = await Promise.allSettled(
        eventIds.map((id) =>
          apiFetch<TriageReport>(`/triage/${id}`).then((t) => ({ id, triage: t }))
        )
      );
      const map: Record<string, TriageReport> = {};
      for (const result of results) {
        if (result.status === 'fulfilled') {
          map[result.value.id] = result.value.triage;
        }
      }
      return map;
    },
    { revalidateOnFocus: false, keepPreviousData: true }
  );

  return data ?? {};
}
