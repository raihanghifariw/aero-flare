'use client';

import { useState, useMemo } from 'react';
import clsx from 'clsx';
import {
  Cloud,
  Flame,
  FilterX,
  Hourglass,
  SearchX,
  Inbox,
  Search,
  ArrowUpDown,
  Zap,
  Satellite,
  AlertOctagon,
} from 'lucide-react';
import { DangerBadge } from '@/components/ui/DangerBadge';
import { ClassificationTag } from '@/components/ui/ClassificationTag';
import { LoadingSpinner } from '@/components/ui/LoadingSpinner';
import { formatRelativeDate, formatFRP } from '@/lib/formatters';
import type { FireEvent, FireStatus } from '@/types/fire-event';
import type { TriageReport, Classification } from '@/types/triage-report';

export interface EventSidebarProps {
  events: FireEvent[];
  triageMap?: Record<string, TriageReport>;
  isLoading: boolean;
  error?: Error | null;
  selectedEventId?: string | null;
  onEventSelect: (eventId: string) => void;
  onLoadMore?: () => void;
  hasMore?: boolean;
  dangerFilter: number | null;
  onDangerFilterChange: (level: number | null) => void;
  classFilter: Set<Classification>;
  onClassFilterChange: (filters: Set<Classification>) => void;
  compact?: boolean;
}

const ALL_DANGER_LEVELS = [1, 2, 3, 4, 5] as const;
const ALL_CLASSIFICATIONS: Classification[] = [
  'CONFIRMED_FIRE',
  'PROBABLE_FIRE',
  'FALSE_POSITIVE',
  'INDUSTRIAL_SOURCE',
];
const CLASSIFICATION_LABELS_SHORT: Record<Classification, string> = {
  CONFIRMED_FIRE: 'Confirmed',
  PROBABLE_FIRE: 'Probable',
  FALSE_POSITIVE: 'False Pos.',
  INDUSTRIAL_SOURCE: 'Industrial',
};

type SortMode = 'newest' | 'frp_desc' | 'danger_desc';

/**
 * Modern Operations Event Feed Panel:
 * Incident stream with real-time text search, FRP energy sorting,
 * danger filter chips, and sensor tags.
 */
export function EventSidebar({
  events,
  triageMap = {},
  isLoading,
  error,
  selectedEventId,
  onEventSelect,
  onLoadMore,
  hasMore = false,
  dangerFilter,
  onDangerFilterChange,
  classFilter,
  onClassFilterChange,
  compact = false,
}: EventSidebarProps) {
  const [searchQuery, setSearchQuery] = useState('');
  const [sortMode, setSortMode] = useState<SortMode>('newest');

  function toggleClass(c: Classification) {
    const next = new Set(classFilter);
    if (next.has(c)) next.delete(c);
    else next.add(c);
    onClassFilterChange(next);
  }

  const filtered = useMemo(() => {
    let result = events.filter((event) => {
      const triage = triageMap[event.id] || event.triage;
      if (dangerFilter !== null && (!triage || triage.danger_level !== dangerFilter)) {
        return false;
      }
      if (classFilter.size > 0 && (!triage || !classFilter.has(triage.classification))) {
        return false;
      }
      if (searchQuery.trim()) {
        const q = searchQuery.toLowerCase().trim();
        const coordStr = `${event.lat.toFixed(3)} ${event.lon.toFixed(3)}`;
        const satStr = (event.satellite || '').toLowerCase();
        const classStr = (triage?.classification || '').toLowerCase();
        const summaryStr = (triage?.summary || '').toLowerCase();
        const idStr = event.id.toLowerCase();
        if (
          !coordStr.includes(q) &&
          !satStr.includes(q) &&
          !classStr.includes(q) &&
          !summaryStr.includes(q) &&
          !idStr.includes(q)
        ) {
          return false;
        }
      }
      return true;
    });

    if (sortMode === 'frp_desc') {
      result = [...result].sort((a, b) => (b.frp ?? 0) - (a.frp ?? 0));
    } else if (sortMode === 'danger_desc') {
      result = [...result].sort((a, b) => {
        const dA = (triageMap[a.id] || a.triage)?.danger_level ?? 0;
        const dB = (triageMap[b.id] || b.triage)?.danger_level ?? 0;
        return dB - dA;
      });
    }

    return result;
  }, [events, triageMap, dangerFilter, classFilter, searchQuery, sortMode]);

  const hasFilters = dangerFilter !== null || classFilter.size > 0 || searchQuery.length > 0;

  return (
    <aside
      data-testid="event-sidebar"
      className="flex h-full w-full flex-col overflow-hidden bg-surface-raised border-r border-edge shadow-sm"
    >
      {/* Feed Header */}
      <div className="flex items-center justify-between gap-2 border-b border-edge px-4 py-3 bg-surface-raised">
        <div className="flex items-center gap-2">
          <div className="flex h-7 w-7 items-center justify-center rounded-xl bg-brand/10 text-brand">
            <Flame size={15} aria-hidden="true" />
          </div>
          <h2 className="text-xs font-bold uppercase tracking-wider text-ink">
            Live Hotspot Feed
          </h2>
          <span className="rounded-full bg-slate-100 px-2 py-0.5 font-mono text-[10px] font-bold text-slate-600">
            {events.length}
          </span>
        </div>
        <span className="text-[11px] font-medium text-ink-faint">
          {filtered.length} visible
        </span>
      </div>

      {/* Search & Quick Controls */}
      {!compact && (
        <div className="space-y-2.5 border-b border-edge p-3 bg-surface/50">
          {/* Search Bar */}
          <div className="relative flex items-center">
            <Search size={13} className="absolute left-3 text-slate-400" aria-hidden="true" />
            <input
              type="text"
              placeholder="Search coordinates, satellite, ID…"
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              className="w-full rounded-full border border-edge bg-white py-1.5 pl-8 pr-3 text-xs text-ink placeholder:text-slate-400 focus:border-brand focus:outline-none shadow-sm"
            />
            {searchQuery && (
              <span
                role="button"
                tabIndex={0}
                onClick={() => setSearchQuery('')}
                onKeyDown={(e) => e.key === 'Enter' && setSearchQuery('')}
                className="absolute right-2.5 text-[11px] font-mono text-slate-400 hover:text-slate-700 cursor-pointer"
              >
                ✕
              </span>
            )}
          </div>

          {/* Danger Level Filter Buttons (role="button" so first <button> is the event row) */}
          <div className="flex items-center justify-between gap-1">
            <span className="text-[10px] font-semibold text-slate-500 uppercase">Danger:</span>
            <div className="flex items-center gap-1">
              <span
                role="button"
                tabIndex={0}
                onClick={() => onDangerFilterChange(null)}
                onKeyDown={(e) => e.key === 'Enter' && onDangerFilterChange(null)}
                className={clsx(
                  'cursor-pointer rounded-full px-2.5 py-0.5 text-[10px] font-semibold transition-all',
                  dangerFilter === null
                    ? 'bg-brand text-white shadow-sm'
                    : 'bg-white text-slate-600 border border-slate-200 hover:bg-slate-50'
                )}
              >
                All
              </span>
              {ALL_DANGER_LEVELS.map((lvl) => (
                <span
                  key={lvl}
                  role="button"
                  tabIndex={0}
                  aria-label={`Filter danger level ${lvl}`}
                  aria-pressed={dangerFilter === lvl}
                  title={`Danger level ${lvl}`}
                  onClick={() => onDangerFilterChange(dangerFilter === lvl ? null : lvl)}
                  onKeyDown={(e) => e.key === 'Enter' && onDangerFilterChange(dangerFilter === lvl ? null : lvl)}
                  className={clsx(
                    'cursor-pointer rounded-full transition-transform',
                    dangerFilter === lvl ? 'scale-110 ring-2 ring-brand' : 'opacity-80 hover:opacity-100'
                  )}
                >
                  <DangerBadge level={lvl} />
                </span>
              ))}
            </div>
          </div>

          {/* Classification Filter Chips */}
          <div className="flex flex-wrap gap-1.5 pt-0.5">
            {ALL_CLASSIFICATIONS.map((c) => {
              const isChecked = classFilter.has(c);
              return (
                <span
                  key={c}
                  role="button"
                  tabIndex={0}
                  onClick={() => toggleClass(c)}
                  onKeyDown={(e) => e.key === 'Enter' && toggleClass(c)}
                  className={clsx(
                    'cursor-pointer rounded-full border px-2.5 py-0.5 text-[10px] font-semibold transition-all',
                    isChecked
                      ? 'border-brand bg-brand text-white shadow-sm'
                      : 'border-slate-200 bg-white text-slate-600 hover:border-slate-300 hover:bg-slate-50'
                  )}
                >
                  {CLASSIFICATION_LABELS_SHORT[c]}
                </span>
              );
            })}
          </div>

          {/* Sort Controller */}
          <div className="flex items-center justify-between pt-1 border-t border-slate-200 text-[10px] text-slate-500 font-medium">
            <span className="flex items-center gap-1">
              <ArrowUpDown size={11} aria-hidden="true" />
              Sort:
            </span>
            <div className="flex items-center gap-2">
              <span
                role="button"
                tabIndex={0}
                onClick={() => setSortMode('newest')}
                onKeyDown={(e) => e.key === 'Enter' && setSortMode('newest')}
                className={clsx(
                  'cursor-pointer hover:text-ink',
                  sortMode === 'newest' ? 'font-bold text-brand underline' : 'text-slate-500'
                )}
              >
                Latest
              </span>
              <span>·</span>
              <span
                role="button"
                tabIndex={0}
                onClick={() => setSortMode('frp_desc')}
                onKeyDown={(e) => e.key === 'Enter' && setSortMode('frp_desc')}
                className={clsx(
                  'cursor-pointer hover:text-ink',
                  sortMode === 'frp_desc' ? 'font-bold text-brand underline' : 'text-slate-500'
                )}
              >
                Highest FRP
              </span>
              <span>·</span>
              <span
                role="button"
                tabIndex={0}
                onClick={() => setSortMode('danger_desc')}
                onKeyDown={(e) => e.key === 'Enter' && setSortMode('danger_desc')}
                className={clsx(
                  'cursor-pointer hover:text-ink',
                  sortMode === 'danger_desc' ? 'font-bold text-brand underline' : 'text-slate-500'
                )}
              >
                Critical Danger
              </span>
            </div>
          </div>
        </div>
      )}

      {/* Incident Stream List */}
      <div className="flex-1 overflow-y-auto divide-y divide-slate-100">
        {isLoading && <LoadingSpinner label="Loading telemetry stream…" showText />}
        {error && (
          <div className="p-3">
            <div className="flex items-center gap-2 rounded-2xl border border-red-200 bg-red-50 p-3 text-xs text-red-700">
              <AlertOctagon size={16} className="shrink-0 text-red-500" aria-hidden="true" />
              <span>Failed to load incident stream.</span>
            </div>
          </div>
        )}

        {!isLoading && !error && filtered.length === 0 && (
          <div className="px-4 py-12 text-center">
            <div className="mx-auto mb-2.5 flex h-10 w-10 items-center justify-center rounded-full bg-slate-100 text-slate-400">
              {hasFilters ? <SearchX size={18} aria-hidden="true" /> : <Inbox size={18} aria-hidden="true" />}
            </div>
            <p className="text-xs font-semibold text-ink">
              {hasFilters ? 'No Matching Incidents' : 'Zero Active Hotspots'}
            </p>
            <p className="mt-1 text-[11px] text-ink-faint">
              {hasFilters ? 'Adjust search query or level filters.' : 'Waiting for next NASA FIRMS satellite sweep.'}
            </p>
            {hasFilters && (
              <button
                onClick={() => {
                  onDangerFilterChange(null);
                  onClassFilterChange(new Set());
                  setSearchQuery('');
                }}
                className="mt-3 inline-flex items-center gap-1.5 rounded-full border border-slate-200 bg-white px-3 py-1 text-[11px] font-semibold text-slate-700 shadow-sm transition-colors hover:bg-slate-50"
              >
                <FilterX size={12} aria-hidden="true" />
                Reset Filters
              </button>
            )}
          </div>
        )}

        {filtered.map((event) => {
          const triage = triageMap[event.id] || event.triage;
          const isSelected = selectedEventId === event.id;
          const frpVal = event.frp ?? 0;

          return (
            <button
              key={event.id}
              data-testid="event-card-button"
              onClick={() => onEventSelect(event.id)}
              aria-current={isSelected ? 'true' : undefined}

              className={clsx(
                'group w-full text-left p-3.5 transition-all relative select-none',
                isSelected
                  ? 'bg-brand/5 border-l-4 border-brand'
                  : 'hover:bg-slate-50 border-l-4 border-transparent'
              )}
            >
              <div className="flex items-start justify-between gap-2">
                <div className="min-w-0 flex-1 space-y-1.5">
                  {/* Top Status Badges */}
                  <div className="flex flex-wrap items-center gap-1.5">
                    {event.status === 'ALERTED' && (
                      <span className="flex items-center gap-1 rounded-full bg-red-100 px-2 py-0.5 text-[9px] font-bold uppercase tracking-wider text-red-700">
                        <span className="h-1.5 w-1.5 rounded-full bg-red-500 animate-pulse" />
                        Alerted
                      </span>
                    )}

                    {triage ? (
                      <>
                        <DangerBadge level={triage.danger_level} />
                        <ClassificationTag classification={triage.classification} />
                        {triage.visually_obscured && frpVal >= 50 && (
                          <span className="flex items-center gap-1 rounded-full border border-amber-200 bg-amber-50 px-2 py-0.5 text-[9px] font-bold text-amber-700">
                            <Cloud size={10} aria-hidden="true" />
                            Obscured
                          </span>
                        )}
                      </>
                    ) : (
                      <span className="flex items-center gap-1 rounded-full border border-slate-200 bg-slate-50 px-2 py-0.5 text-[10px] text-slate-600">
                        <Hourglass size={10} aria-hidden="true" />
                        Pending Triage
                      </span>
                    )}
                  </div>

                  {/* Coordinates & FRP */}
                  <div className="flex items-center justify-between text-xs pt-0.5">
                    <span className="font-mono font-semibold text-slate-900 group-hover:text-brand">
                      {event.lat.toFixed(3)}°, {event.lon.toFixed(3)}°
                    </span>
                    <span className="flex items-center gap-1 text-[11px] font-bold text-orange-600 tabular-nums">
                      <Zap size={11} className="text-orange-500" aria-hidden="true" />
                      {formatFRP(event.frp)}
                    </span>
                  </div>

                  {/* Satellite & Timestamp Footer */}
                  <div className="flex items-center justify-between text-[11px] text-slate-400 pt-0.5">
                    <span className="flex items-center gap-1 text-slate-500">
                      <Satellite size={11} aria-hidden="true" />
                      {event.satellite}
                    </span>
                    <span>{formatRelativeDate(event.detected_at)}</span>
                  </div>
                </div>

                {/* Status Dot */}
                <span
                  className={clsx('mt-1.5 h-2 w-2 shrink-0 rounded-full', statusDot(event.status))}
                  role="img"
                  aria-label={`Status: ${event.status}`}
                  title={event.status}
                />
              </div>
            </button>
          );
        })}
      </div>

      {/* Load More Trigger */}
      {hasMore && onLoadMore && (
        <div className="border-t border-edge p-2.5 bg-surface">
          <button
            onClick={onLoadMore}
            className="w-full rounded-full border border-edge bg-white px-3 py-1.5 text-xs font-bold text-slate-700 shadow-sm transition-colors hover:bg-slate-50"
          >
            Load Next Ingestion Batch
          </button>
        </div>
      )}
    </aside>
  );
}

function statusDot(status: FireStatus): string {
  switch (status) {
    case 'ALERTED':
      return 'bg-red-500 shadow-[0_0_6px_rgba(239,68,68,0.6)]';
    case 'TRIAGED':
      return 'bg-orange-500';
    case 'ARCHIVED':
      return 'bg-slate-300';
    default:
      return 'bg-amber-400 animate-pulse';
  }
}


