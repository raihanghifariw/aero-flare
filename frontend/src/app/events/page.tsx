'use client';

import { useState } from 'react';
import Link from 'next/link';
import clsx from 'clsx';
import { useFireEvents } from '@/hooks/useFireEvents';
import { LoadingSpinner } from '@/components/ui/LoadingSpinner';
import { ErrorAlert } from '@/components/ui/ErrorAlert';
import { EventTimeline } from '@/components/charts/EventTimeline';
import { DangerBadge } from '@/components/ui/DangerBadge';
import { ClassificationTag } from '@/components/ui/ClassificationTag';
import { TriageSourceBadge } from '@/components/ui/TriageSourceBadge';
import { useTriageMap } from '@/hooks/useTriageMap';
import { formatDate, formatCoords, formatFRP } from '@/lib/formatters';
import type { FireEvent, FireStatus } from '@/types/fire-event';

const PAGE_SIZE = 25;

const STATUS_OPTIONS: { value: FireStatus | ''; label: string }[] = [
  { value: '', label: 'All statuses' },
  { value: 'PENDING', label: 'Pending' },
  { value: 'TRIAGED', label: 'Triaged' },
  { value: 'ALERTED', label: 'Alerted' },
  { value: 'ARCHIVED', label: 'Archived' },
];

export default function EventsPage() {
  const [page, setPage] = useState(1);
  const [statusFilter, setStatusFilter] = useState<FireStatus | ''>('');

  const { data, isLoading, error, mutate } = useFireEvents({
    page,
    limit: PAGE_SIZE,
    status: statusFilter,
  });

  const events: FireEvent[] = data?.data ?? [];
  const triageMap = useTriageMap(events.map((event) => event.id));
  const total = data?.total ?? 0;
  const totalPages = Math.ceil(total / PAGE_SIZE);

  return (
    <div className="mx-auto max-w-7xl px-4 py-6">
      <div className="mb-6 flex items-center justify-between flex-wrap gap-3">
        <div>
          <h1 className="text-xl font-bold text-gray-800">Fire Events</h1>
          <p className="text-sm text-gray-500">{total} total events</p>
        </div>

        {/* Status filter */}
        <select
          value={statusFilter}
          onChange={(e) => {
            setStatusFilter(e.target.value as FireStatus | '');
            setPage(1);
          }}
          className="rounded-lg border border-gray-200 px-3 py-1.5 text-sm text-gray-700 focus:outline-none focus:ring-2 focus:ring-orange-400"
        >
          {STATUS_OPTIONS.map((opt) => (
            <option key={opt.value} value={opt.value}>
              {opt.label}
            </option>
          ))}
        </select>
      </div>

      {/* Timeline chart */}
      {events.length > 0 && (
        <div className="mb-6 rounded-xl border border-gray-200 bg-white p-4">
          <EventTimeline events={events} />
        </div>
      )}

      {/* States */}
      {isLoading && <LoadingSpinner size="lg" label="Loading events…" />}
      {error && (
        <ErrorAlert
          message="Failed to load fire events."
          onRetry={() => mutate()}
        />
      )}

      {/* Table */}
      {!isLoading && !error && (
        <div className="overflow-x-auto rounded-xl border border-gray-200 bg-white">
          <table className="min-w-full divide-y divide-gray-100 text-sm">
            <thead className="bg-gray-50">
              <tr>
                {['Danger', 'Classification', 'Source', 'Location', 'FRP', 'Detected', 'Status', ''].map(
                  (col) => (
                    <th
                      key={col}
                      className="px-4 py-2.5 text-left text-xs font-semibold text-gray-500 uppercase tracking-wide"
                    >
                      {col}
                    </th>
                  )
                )}
              </tr>
            </thead>
            <tbody className="divide-y divide-gray-100">
              {events.length === 0 && (
                <tr>
                  <td colSpan={8} className="px-4 py-8 text-center text-gray-400">
                    No fire events detected in selected range
                  </td>
                </tr>
              )}
              {events.map((event) => (
                <tr key={event.id} className="hover:bg-orange-50 transition-colors">
                  {(() => {
                    const triage = triageMap[event.id];
                    return (
                      <>
                        <td className="px-4 py-2.5">
                          {triage ? <DangerBadge level={triage.danger_level} /> : <span className="text-xs text-gray-400">Pending</span>}
                        </td>
                        <td className="px-4 py-2.5">
                          {triage ? <ClassificationTag classification={triage.classification} /> : <span className="text-xs text-gray-300">—</span>}
                        </td>
                        <td className="px-4 py-2.5">
                          {triage ? <TriageSourceBadge source={triage.triage_source} /> : <span className="text-xs text-gray-300">—</span>}
                        </td>
                      </>
                    );
                  })()}
                  <td className="px-4 py-2.5 text-gray-600 tabular-nums">
                    {formatCoords(event.lat, event.lon)}
                  </td>
                  <td className="px-4 py-2.5 text-gray-600 tabular-nums">
                    {formatFRP(event.frp)}
                  </td>
                  <td className="px-4 py-2.5 text-gray-500">
                    {formatDate(event.detected_at, 'dd MMM, HH:mm')}
                  </td>
                  <td className="px-4 py-2.5">
                    <StatusPill status={event.status} />
                  </td>
                  <td className="px-4 py-2.5">
                    <Link
                      href={`/events/${event.id}`}
                      className="text-xs text-orange-600 hover:text-orange-800 font-medium"
                    >
                      View →
                    </Link>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}

      {/* Pagination */}
      {totalPages > 1 && (
        <div className="mt-4 flex items-center justify-between">
          <button
            onClick={() => setPage((p) => Math.max(1, p - 1))}
            disabled={page === 1}
            className={clsx(
              'rounded-lg border px-3 py-1.5 text-sm transition-colors',
              page === 1
                ? 'border-gray-100 text-gray-300 cursor-not-allowed'
                : 'border-gray-200 text-gray-700 hover:bg-gray-50'
            )}
          >
            ← Previous
          </button>
          <span className="text-xs text-gray-500">
            Page {page} of {totalPages}
          </span>
          <button
            onClick={() => setPage((p) => Math.min(totalPages, p + 1))}
            disabled={page === totalPages}
            className={clsx(
              'rounded-lg border px-3 py-1.5 text-sm transition-colors',
              page === totalPages
                ? 'border-gray-100 text-gray-300 cursor-not-allowed'
                : 'border-gray-200 text-gray-700 hover:bg-gray-50'
            )}
          >
            Next →
          </button>
        </div>
      )}
    </div>
  );
}

function StatusPill({ status }: { status: FireStatus }) {
  const classes: Record<FireStatus, string> = {
    PENDING: 'bg-yellow-100 text-yellow-800',
    TRIAGED: 'bg-orange-100 text-orange-800',
    ALERTED: 'bg-red-100 text-red-800',
    ARCHIVED: 'bg-gray-100 text-gray-600',
  };
  return (
    <span className={clsx('px-2 py-0.5 rounded-full text-xs font-medium', classes[status])}>
      {status.charAt(0) + status.slice(1).toLowerCase()}
    </span>
  );
}
