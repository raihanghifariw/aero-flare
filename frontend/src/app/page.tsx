'use client';

import { useMemo, useState } from 'react';
import dynamic from 'next/dynamic';
import { ChevronDown, ChevronUp, List } from 'lucide-react';
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
      <div className="flex h-full items-center justify-center bg-surface">
        <LoadingSpinner size="lg" label="Initializing cartography…" showText />
      </div>
    ),
  }
);

// Time range options (hours)
const TIME_RANGE_OPTIONS = [
  { label: '1D', hours: 24 },
  { label: '2D', hours: 48 },
  { label: '7D', hours: 168 },
] as const;
type TimeRangeHours = 24 | 48 | 168;


export default function DashboardPage() {
  const [page, setPage] = useState(1);
  const [selectedEventId, setSelectedEventId] = useState<string | null>(null);
  const [dangerFilter, setDangerFilter] = useState<number | null>(null);
  const [classFilter, setClassFilter] = useState<Set<Classification>>(new Set());
  const [timeRange, setTimeRange] = useState<TimeRangeHours>(48);
  const [mobileListOpen, setMobileListOpen] = useState(false);

  // Compute date_from from selected time range
  const dateFrom = useMemo(
    () => new Date(Date.now() - timeRange * 60 * 60 * 1000).toISOString(),
    [timeRange]
  );

  // Compute classification filter for backend query when a single classification is checked
  const classParam = useMemo(() => {
    if (classFilter.size === 1) {
      return Array.from(classFilter)[0];
    }
    return undefined;
  }, [classFilter]);

  // Fire events (polled every 5 min)
  const {
    data: eventsData,
    isLoading: eventsLoading,
    error: eventsError,
    mutate: refetchEvents,
  } = useFireEvents({
    page,
    limit: 300,
    date_from: dateFrom,
    ...(dangerFilter !== null && { danger_level: dangerFilter }),
    ...(classParam && { classification: classParam }),
  });

  // Pipeline stats
  const { data: stats, isLoading: statsLoading } = useSWR<PipelineStats>(
    '/stats',
    apiFetch,
    { refreshInterval: 60_000, revalidateOnFocus: false }
  );

  const events: FireEvent[] = useMemo(() => eventsData?.data ?? [], [eventsData?.data]);
  const hasMore = eventsData ? eventsData.total > eventsData.page * eventsData.limit : false;

  // Batch-fetch triage data for all loaded events
  const triageMap = useTriageMap(events);

  const visibleEvents = useMemo(() => events.filter((event) => {
    const triage = triageMap[event.id] || event.triage;
    if (dangerFilter !== null && triage?.danger_level !== dangerFilter) return false;
    if (classFilter.size > 0 && (!triage || !classFilter.has(triage.classification))) return false;
    return true;
  }), [classFilter, dangerFilter, events, triageMap]);

  const selectedEvent = events.find((e) => e.id === selectedEventId) ?? null;

  return (
    <div className="flex h-full flex-col bg-surface">
      <StatsBar stats={stats} isLoading={statsLoading} />

      <div className="flex flex-1 overflow-hidden">
        {/* Modern Map Container — 70% desktop */}
        <div
          className="relative flex-1 md:flex-[7]"
          data-testid="fire-map-container"
        >
          {/* Top-Left Telemetry Badge */}
          <div className="pointer-events-none absolute left-4 top-4 z-[400] hidden rounded-2xl border border-edge bg-white/95 px-4 py-2.5 shadow-md backdrop-blur sm:block">
            <div className="flex items-center gap-2">
              <span className="h-2 w-2 rounded-full bg-brand animate-pulse" />
              <p className="text-[11px] font-bold uppercase tracking-wider text-brand">
                Live Cartography
              </p>
            </div>
            <p className="mt-0.5 text-xs font-semibold text-slate-700">
              Indonesia · {visibleEvents.length} Active Hotspots
            </p>
          </div>

          {/* Top-Right Time Range Selector */}
          <div className="pointer-events-auto absolute right-4 top-4 z-[400] hidden items-center gap-1 rounded-full border border-edge bg-white/95 p-1 shadow-md backdrop-blur sm:flex">
            <span className="px-2 text-[10px] font-bold text-slate-400">RANGE</span>
            {TIME_RANGE_OPTIONS.map(({ label, hours }) => (
              <button
                key={hours}
                aria-pressed={timeRange === hours}
                onClick={() => { setTimeRange(hours as TimeRangeHours); setPage(1); }}
                className={`rounded-full px-3 py-1 text-xs font-bold transition-all ${
                  timeRange === hours
                    ? 'bg-brand text-white shadow-sm'
                    : 'text-slate-600 hover:bg-slate-50 hover:text-ink'
                }`}
              >
                {label}
              </button>
            ))}
          </div>

          {/* Network Interruption Alert */}
          {eventsError && (
            <div className="absolute left-4 right-4 top-4 z-[400]">
              <ErrorAlert
                message="Telemetry ingestion feed interrupted. Backend service unreachable or offline."
                onRetry={() => {
                  refetchEvents();
                }}
              />
            </div>
          )}


          <FireMap
            events={visibleEvents}
            triageMap={triageMap}
            selectedEventId={selectedEventId}
            onMarkerSelect={setSelectedEventId}
          />
        </div>

        {/* Sidebar Panel — 30% desktop */}
        <div
          className={`
            hidden md:flex md:flex-[3] md:max-w-xs lg:max-w-sm
            border-l border-edge bg-surface-raised shadow-sm
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

        {/* Mobile collapsible incident drawer */}
        <div className="fixed bottom-0 left-0 right-0 z-30 md:hidden">
          {mobileListOpen && (
            <div className="max-h-64 overflow-hidden border-t border-edge bg-surface-raised shadow-xl">
              <div className="max-h-64 overflow-y-auto">
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
                  compact
                />
              </div>
            </div>
          )}
          <button
            onClick={() => setMobileListOpen((open) => !open)}
            aria-expanded={mobileListOpen}
            className="flex w-full items-center justify-center gap-2 border-t border-edge bg-white/95 py-3 text-xs font-bold uppercase tracking-wider text-ink backdrop-blur shadow-xl"
          >
            <List size={14} className="text-brand" aria-hidden="true" />
            <span>{mobileListOpen ? 'Hide Incident Feed' : `View Incident Feed (${events.length})`}</span>
            {mobileListOpen
              ? <ChevronDown size={14} aria-hidden="true" />
              : <ChevronUp size={14} aria-hidden="true" />}
          </button>
        </div>
      </div>

      {/* Triage Inspector Modal / Drawer */}
      <TriageModal event={selectedEvent} onClose={() => setSelectedEventId(null)} />
    </div>
  );
}

