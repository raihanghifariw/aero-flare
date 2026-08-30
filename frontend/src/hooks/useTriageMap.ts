import useSWR from 'swr';
import { apiFetch } from '@/lib/api';
import type { FireEvent } from '@/types/fire-event';
import type { TriageReport } from '@/types/triage-report';

/**
 * Extracts embedded triage reports from FireEvents and fetches missing reports in parallel.
 * Returns a lookup map: event_id → TriageReport.
 */
export function useTriageMap(eventsOrIds: (FireEvent | string)[]): Record<string, TriageReport> {
  const embeddedMap: Record<string, TriageReport> = {};
  const missingIds: string[] = [];

  for (const item of eventsOrIds) {
    if (typeof item === 'string') {
      missingIds.push(item);
    } else if (item.triage) {
      embeddedMap[item.id] = item.triage;
    } else if (item.status !== 'PENDING') {
      missingIds.push(item.id);
    }
  }


  const key = missingIds.length > 0 ? missingIds.slice().sort().join(',') : null;

  const { data } = useSWR<Record<string, TriageReport>>(
    key ? `__triage_map__${key}` : null,
    async () => {
      const results = await Promise.allSettled(
        missingIds.map((id) =>
          apiFetch<TriageReport>(`/triage/${id}`).then((t) => ({ id, triage: t }))
        )
      );
      const resMap: Record<string, TriageReport> = {};
      for (const result of results) {
        if (result.status === 'fulfilled') {
          resMap[result.value.id] = result.value.triage;
        }
      }
      return resMap;
    },
    { revalidateOnFocus: false, keepPreviousData: true }
  );

  return { ...embeddedMap, ...(data ?? {}) };
}
