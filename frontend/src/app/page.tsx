'use client';

import { useMemo, useState } from 'react';
import dynamic from 'next/dynamic';
import useSWR from 'swr';
import { useFireEvents } from '@/hooks/useFireEvents';
import { useTriageMap } from '@/hooks/useTriageMap';
import { StatsBar } from '@/components/panels/StatsBar';
import { EventSidebar } from '@/components/panels/EventSidebar';
import { TriageModal } from '@/components/panels/TriageModal';
import { LoadingSpinner } from '@/components/ui/LoadingSpinner';
import { ErrorAlert } from '@/components/ui/ErrorAlert';
import type { FireEvent } from '@/types/fire-event';
import type { PipelineStats } from '@/components/panels/StatsBar';
import { apiFetch } from '@/lib/api';
import type { Classification } from '@/types/triage-report';

// CRITICAL: Leaflet requires browser APIs — must be loaded client-side only
const FireMap = dynamic(
  () => import('@/components/map/FireMap').then((m) => m.FireMap),
  {
    ssr: false,
    loading: () => (
      <div className="flex h-full items-center justify-center bg-gray-100">
        <LoadingSpinner size="lg" label="Loading map…" />
      </div>
    ),
  }
);

// Time range options (hours)
const TIME_RANGE_OPTIONS = [
  { label: '24h', hours: 24 },
  { label: '48h', hours: 48 },
  { label: '7d', hours: 168 },
] as const;
type TimeRangeHours = 24 | 48 | 168;

export default function DashboardPage() {
  const [page, setPage] = useState(1);
  const [selectedEventId, setSelectedEventId] = useState<string | null>(null);
  const [dangerFilter, setDangerFilter] = useState<number | null>(null);
  const [classFilter, setClassFilter] = useState<Set<Classification>>(new Set());
  const [timeRange, setTimeRange] = useState<TimeRangeHours>(24);

  // Compute date_from from selected time range
  const dateFrom = useMemo(
    () => new Date(Date.now() - timeRange * 60 * 60 * 1000).toISOString(),
    [timeRange]
  );

  // Fire events (polled every 5 min) — scoped to selected time range
  const {
    data: eventsData,
    isLoading: eventsLoading,
    error: eventsError,
    mutate: refetchEvents,
  } = useFireEvents({
    page,
    limit: 100,
    date_from: dateFrom,
    ...(dangerFilter !== null && { danger_level: dangerFilter }),
  });

  // Pipeline stats
  const { data: stats, isLoading: statsLoading } = useSWR<PipelineStats>(
    '/stats',
    apiFetch,
    { refreshInterval: 60_000, revalidateOnFocus: false }
  );

  const events: FireEvent[] = useMemo(() => eventsData?.data ?? [], [eventsData?.data]);
  const hasMore = eventsData ? eventsData.total > eventsData.page * eventsData.limit : false;

  // Batch-fetch triage data for all loaded events so the sidebar can show
  // classification + danger badges without waiting for modal open.
  const triageMap = useTriageMap(events);

  const visibleEvents = useMemo(() => events.filter((event) => {
    const triage = triageMap[event.id];
    if (dangerFilter !== null && triage?.danger_level !== dangerFilter) return false;
    if (classFilter.size > 0 && (!triage || !classFilter.has(triage.classification))) return false;
    return true;
  }), [classFilter, dangerFilter, events, triageMap]);

  const selectedEvent = events.find((e) => e.id === selectedEventId) ?? null;

  return (
    <div className="flex h-full flex-col">
      <StatsBar stats={stats} isLoading={statsLoading} />

      <div className="flex flex-1 overflow-hidden">
        {/* Map — takes 70% on desktop, full width on mobile */}
        <div
          className="relative flex-1 md:flex-[7]"
          data-testid="fire-map-container"
        >
          <div className="pointer-events-none absolute left-4 top-4 z-10 hidden rounded-lg border border-white/70 bg-slate-950/85 px-3 py-2 text-white shadow-lg backdrop-blur-sm sm:block">
            <p className="text-[10px] font-semibold uppercase tracking-[0.18em] text-orange-300">Live detection map</p>
            <p className="mt-0.5 text-xs text-slate-300">Indonesia · NASA FIRMS</p>
          </div>

          {/* Time range selector */}
          <div className="pointer-events-auto absolute right-4 top-4 z-10 hidden sm:flex items-center gap-1 rounded-lg border border-white/70 bg-slate-950/85 px-2 py-1.5 shadow-lg backdrop-blur-sm">
            <span className="text-[10px] text-slate-400 mr-1">Range:</span>
            {TIME_RANGE_OPTIONS.map(({ label, hours }) => (
              <button
                key={hours}
                onClick={() => { setTimeRange(hours as TimeRangeHours); setPage(1); }}
                className={`px-2 py-0.5 rounded text-[11px] font-medium transition-colors ${
                  timeRange === hours
                    ? 'bg-orange-500 text-white'
                    : 'text-slate-300 hover:text-white hover:bg-white/10'
                }`}
              >
                {label}
              </button>
            ))}
          </div>
          {eventsError && (
            <div className="absolute top-3 left-3 right-3 z-10">
              <ErrorAlert
                message="Failed to load fire events. Map may be incomplete."
                onRetry={() => refetchEvents()}
              />
            </div>
          )}

          <FireMap
            key={visibleEvents.map((event) => event.id).join('|') || 'empty'}
            events={visibleEvents}
            triageMap={triageMap}
            selectedEventId={selectedEventId}
            onMarkerSelect={setSelectedEventId}
          />
        </div>

        {/* Sidebar — 30% on desktop, hidden on mobile (event list swipes up) */}
        <div
          className={`
            hidden md:flex md:flex-[3] md:max-w-xs lg:max-w-sm
            border-l border-gray-200
          `}
        >
          <EventSidebar
            events={events}
            triageMap={triageMap}
            isLoading={eventsLoading}
            error={eventsError ?? null}
            selectedEventId={selectedEventId}
            onEventSelect={setSelectedEventId}
            dangerFilter={dangerFilter}
            onDangerFilterChange={setDangerFilter}
            classFilter={classFilter}
            onClassFilterChange={setClassFilter}
            hasMore={hasMore}
            onLoadMore={() => setPage((p) => p + 1)}
          />
        </div>

        {/* Mobile: bottom drawer event list toggle */}
        <div className="md:hidden fixed bottom-0 left-0 right-0 z-30">
          {/* Simplified mobile list — full sidebar is available on tablet+ */}
          <div className="max-h-48 overflow-y-auto bg-white border-t border-gray-200 shadow-lg">
            <EventSidebar
              events={visibleEvents}
              triageMap={triageMap}
              isLoading={eventsLoading}
              error={eventsError ?? null}
              selectedEventId={selectedEventId}
              onEventSelect={setSelectedEventId}
              dangerFilter={dangerFilter}
              onDangerFilterChange={setDangerFilter}
              classFilter={classFilter}
              onClassFilterChange={setClassFilter}
            />
          </div>
        </div>
      </div>

      {/* Triage Modal (opens when event selected) */}
      <TriageModal event={selectedEvent} onClose={() => setSelectedEventId(null)} />
    </div>
  );
}
