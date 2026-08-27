'use client';

import clsx from 'clsx';
import { DangerBadge } from '@/components/ui/DangerBadge';
import { ClassificationTag } from '@/components/ui/ClassificationTag';
import { LoadingSpinner } from '@/components/ui/LoadingSpinner';
import { ErrorAlert } from '@/components/ui/ErrorAlert';
import { formatRelativeDate } from '@/lib/formatters';
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
  FALSE_POSITIVE: 'False Positive',
  INDUSTRIAL_SOURCE: 'Industrial',
};

/**
 * Scrollable event list panel with danger level + classification filters.
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
}: EventSidebarProps) {
  function toggleClass(c: Classification) {
    const next = new Set(classFilter);
    if (next.has(c)) next.delete(c);
    else next.add(c);
    onClassFilterChange(next);
  }

  const filtered = events;

  const hasFilters = dangerFilter !== null || classFilter.size > 0;

  return (
    <aside
      data-testid="event-sidebar"
      className="flex h-full flex-col overflow-hidden bg-white border-l border-gray-200"
    >
      {/* Header */}
      <div className="border-b border-gray-200 bg-slate-950 px-4 py-3 text-white">
        <div className="flex items-center justify-between gap-2">
          <h2 className="text-sm font-semibold tracking-tight">Fire Events</h2>
          <span className="rounded-full bg-white/10 px-2 py-0.5 text-[10px] font-semibold text-slate-300">
            {events.length} loaded
          </span>
        </div>
        <p className="mt-1 text-xs text-slate-400">
          {filtered.length} visible{hasFilters ? ' with current filters' : ''}
        </p>
      </div>

      {/* Filters */}
      <div className="border-b border-gray-100 px-4 py-2 space-y-2">
        {/* Danger level filter */}
        <div className="flex items-center gap-1.5 flex-wrap">
          <span className="text-xs text-gray-500 mr-1">Level:</span>
          <button
            onClick={() => onDangerFilterChange(null)}
            className={clsx(
              'px-2 py-0.5 rounded text-xs font-medium',
              dangerFilter === null ? 'bg-gray-800 text-white' : 'bg-gray-100 text-gray-600'
            )}
          >
            All
          </button>
          {ALL_DANGER_LEVELS.map((lvl) => (
            <button
              key={lvl}
              aria-label={`Filter danger level ${lvl}`}
              title={`Danger level ${lvl}`}
              onClick={() => onDangerFilterChange(dangerFilter === lvl ? null : lvl)}
              className={clsx(
                'px-2 py-0.5 rounded text-xs font-bold transition-opacity',
                dangerFilter === lvl ? 'opacity-100 ring-2 ring-offset-1 ring-gray-400' : 'opacity-75'
              )}
            >
              <DangerBadge level={lvl} />
            </button>
          ))}
        </div>

        {/* Classification filter checkboxes */}
        <div className="flex flex-wrap gap-1.5">
          {ALL_CLASSIFICATIONS.map((c) => (
            <label
              key={c}
              className="flex items-center gap-1 cursor-pointer"
            >
              <input
                type="checkbox"
                checked={classFilter.has(c)}
                onChange={() => toggleClass(c)}
                className="h-3 w-3 rounded text-orange-500"
              />
              <span className="text-xs text-gray-600">{CLASSIFICATION_LABELS_SHORT[c]}</span>
            </label>
          ))}
        </div>
      </div>

      {/* List */}
      <div className="flex-1 overflow-y-auto divide-y divide-gray-100">
        {isLoading && <LoadingSpinner label="Loading events…" />}
        {error && (
          <div className="p-4">
            <ErrorAlert message="Failed to load fire events." />
          </div>
        )}

        {!isLoading && !error && filtered.length === 0 && (
          <div className="px-5 py-10 text-center">
            <div className="mx-auto mb-3 flex h-9 w-9 items-center justify-center rounded-full bg-slate-100 text-slate-500">
              {hasFilters ? '⌕' : '·'}
            </div>
            <p className="text-sm font-medium text-slate-700">
              {hasFilters ? 'No events match these filters' : 'No fire events detected'}
            </p>
            <p className="mt-1 text-xs leading-relaxed text-slate-400">
              {hasFilters ? 'Try clearing one or more filters.' : 'New satellite detections will appear here.'}
            </p>
            {hasFilters && (
              <button
                onClick={() => {
                  onDangerFilterChange(null);
                  onClassFilterChange(new Set());
                }}
                className="mt-4 rounded-md bg-slate-900 px-3 py-1.5 text-xs font-semibold text-white transition-colors hover:bg-slate-700"
              >
                Clear filters
              </button>
            )}
          </div>
        )}

        {filtered.map((event) => {
          const triage = triageMap[event.id];
          const isSelected = selectedEventId === event.id;

          return (
            <button
              key={event.id}
              onClick={() => onEventSelect(event.id)}
              className={clsx(
                'w-full text-left px-4 py-3 hover:bg-orange-50 transition-colors',
                isSelected && 'bg-orange-50 border-l-2 border-orange-500'
              )}
            >
              <div className="flex items-start justify-between gap-2">
                <div className="min-w-0 flex-1">
                  <div className="flex items-center gap-1.5 mb-0.5 flex-wrap">
                    {event.status === 'ALERTED' && (
                      <span className="rounded bg-red-600 px-1.5 py-0.5 text-[10px] font-bold text-white uppercase tracking-wider animate-pulse">
                        🚨 ALERTED
                      </span>
                    )}
                    {triage ? (
                      <>
                        <DangerBadge level={triage.danger_level} />
                        <ClassificationTag classification={triage.classification} />
                      </>
                    ) : (
                      <span className="text-[10px] text-gray-400 italic">Pending analysis</span>
                    )}
                  </div>
                  <p className="text-xs text-gray-600 truncate">
                    {event.lat.toFixed(3)}°, {event.lon.toFixed(3)}°
                  </p>
                  <p className="text-xs text-gray-400">
                    {formatRelativeDate(event.detected_at)}
                  </p>
                </div>
                <span className={clsx(
                  'mt-1 h-2 w-2 rounded-full shrink-0',
                  statusDot(event.status)
                )} title={event.status} />
              </div>
            </button>
          );
        })}
      </div>

      {/* Load More */}
      {hasMore && onLoadMore && (
        <div className="border-t border-gray-100 p-3">
          <button
            onClick={onLoadMore}
            className="w-full rounded bg-gray-100 px-3 py-1.5 text-xs font-medium text-gray-700 hover:bg-gray-200 transition-colors"
          >
            Load more
          </button>
        </div>
      )}
    </aside>
  );
}

function statusDot(status: FireStatus): string {
  switch (status) {
    case 'ALERTED': return 'bg-red-500';
    case 'TRIAGED': return 'bg-orange-400';
    case 'ARCHIVED': return 'bg-gray-300';
    default: return 'bg-yellow-400';
  }
}
