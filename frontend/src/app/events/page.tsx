'use client';

import { useState, useMemo } from 'react';
import Link from 'next/link';
import clsx from 'clsx';
import {
  ChevronLeft,
  ChevronRight,
  Download,
  Flame,
  Search,
  ExternalLink,
} from 'lucide-react';
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
  { value: '', label: 'All Incident Statuses' },
  { value: 'PENDING', label: 'Pending Triage' },
  { value: 'TRIAGED', label: 'Triaged' },
  { value: 'ALERTED', label: 'Alerted (Active Action)' },
  { value: 'ARCHIVED', label: 'Archived' },
];

export default function EventsPage() {
  const [page, setPage] = useState(1);
  const [statusFilter, setStatusFilter] = useState<FireStatus | ''>('');
  const [searchQuery, setSearchQuery] = useState('');

  const { data, isLoading, error, mutate } = useFireEvents({
    page,
    limit: PAGE_SIZE,
    status: statusFilter,
  });

  const events: FireEvent[] = useMemo(() => data?.data ?? [], [data?.data]);
  const triageMap = useTriageMap(events);
  const total = data?.total ?? 0;
  const totalPages = Math.ceil(total / PAGE_SIZE);

  const filteredEvents = useMemo(() => {
    if (!searchQuery.trim()) return events;
    const q = searchQuery.toLowerCase().trim();
    return events.filter((e) => {
      const triage = triageMap[e.id] || e.triage;
      const coords = `${e.lat.toFixed(4)} ${e.lon.toFixed(4)}`;
      const classification = (triage?.classification || '').toLowerCase();
      const sat = (e.satellite || '').toLowerCase();
      const id = e.id.toLowerCase();
      return (
        coords.includes(q) ||
        classification.includes(q) ||
        sat.includes(q) ||
        id.includes(q)
      );
    });
  }, [events, triageMap, searchQuery]);

  function exportCSV() {
    if (events.length === 0) return;
    const headers = ['ID', 'Detected At', 'Latitude', 'Longitude', 'FRP_MW', 'Satellite', 'Status', 'Danger_Level', 'Classification'];
    const rows = events.map((e) => {
      const t = triageMap[e.id] || e.triage;
      return [
        e.id,
        e.detected_at,
        e.lat,
        e.lon,
        e.frp ?? '',
        e.satellite,
        e.status,
        t?.danger_level ?? '',
        t?.classification ?? '',
      ].join(',');
    });
    const csvContent = 'data:text/csv;charset=utf-8,' + [headers.join(','), ...rows].join('\n');
    const encodedUri = encodeURI(csvContent);
    const link = document.createElement('a');
    link.setAttribute('href', encodedUri);
    link.setAttribute('download', `aeroflare_incidents_${Date.now()}.csv`);
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
  }

  return (
    <div className="mx-auto max-w-7xl space-y-6 px-4 py-8 sm:px-6">
      {/* Top Header & Summary Card */}
      <div className="flex flex-wrap items-center justify-between gap-4 rounded-2xl border border-edge bg-surface-raised p-6 shadow-sm">
        <div>
          <div className="flex items-center gap-2.5">
            <span className="flex h-8 w-8 items-center justify-center rounded-xl bg-brand/10 text-brand">
              <Flame size={18} aria-hidden="true" />
            </span>
            <h1 className="text-xl font-extrabold tracking-tight text-ink">
              Wildfire Incidents Explorer
            </h1>
          </div>
          <p className="mt-1 text-xs text-ink-muted">
            NASA FIRMS Multi-Spectral Detections · <span className="text-brand font-bold">{total} Records</span> Total
          </p>
        </div>

        {/* Action Controls */}
        <div className="flex flex-wrap items-center gap-2.5">
          <button
            onClick={exportCSV}
            className="inline-flex items-center gap-1.5 rounded-full border border-edge bg-white px-4 py-2 text-xs font-semibold text-slate-700 shadow-sm transition-colors hover:bg-slate-50"
          >
            <Download size={13} aria-hidden="true" />
            Export CSV
          </button>

          {/* Status Filter */}
          <div className="relative">
            <select
              value={statusFilter}
              onChange={(e) => {
                setStatusFilter(e.target.value as FireStatus | '');
                setPage(1);
              }}
              className="rounded-full border border-edge bg-white px-4 py-2 text-xs font-medium text-slate-700 shadow-sm focus:border-brand focus:outline-none"
            >
              {STATUS_OPTIONS.map((opt) => (
                <option key={opt.value} value={opt.value}>
                  {opt.label}
                </option>
              ))}
            </select>
          </div>
        </div>
      </div>

      {/* Timeline Trend Graph */}
      {events.length > 0 && (
        <div className="rounded-2xl border border-edge bg-surface-raised p-5 shadow-sm">
          <EventTimeline events={events} />
        </div>
      )}

      {/* Search Input */}
      <div className="relative flex items-center">
        <Search size={15} className="absolute left-4 text-slate-400" aria-hidden="true" />
        <input
          type="text"
          placeholder="Filter page by coordinates, satellite, classification, or ID…"
          value={searchQuery}
          onChange={(e) => setSearchQuery(e.target.value)}
          className="w-full rounded-full border border-edge bg-surface-raised py-3 pl-11 pr-5 text-xs text-ink placeholder:text-slate-400 focus:border-brand focus:outline-none shadow-sm"
        />
        {searchQuery && (
          <button
            onClick={() => setSearchQuery('')}
            className="absolute right-4 text-xs font-mono text-slate-400 hover:text-slate-700"
          >
            ✕
          </button>
        )}
      </div>

      {/* States */}
      {isLoading && <LoadingSpinner size="lg" label="Loading incidents stream…" showText />}
      {error && (
        <ErrorAlert
          message="Failed to fetch incidents stream from telemetry API."
          onRetry={() => mutate()}
        />
      )}

      {/* Incident Records Table */}
      {!isLoading && !error && (
        <div className="overflow-hidden rounded-2xl border border-edge bg-surface-raised shadow-sm">
          <div className="overflow-x-auto">
            <table className="min-w-full divide-y divide-edge text-left text-xs">
              <thead>
                <tr className="bg-surface">
                  <th className="px-5 py-3.5 font-bold uppercase tracking-wider text-slate-500 text-[10px]">
                    Danger
                  </th>
                  <th className="px-5 py-3.5 font-bold uppercase tracking-wider text-slate-500 text-[10px]">
                    Classification
                  </th>
                  <th className="px-5 py-3.5 font-bold uppercase tracking-wider text-slate-500 text-[10px]">
                    Source
                  </th>
                  <th className="px-5 py-3.5 font-bold uppercase tracking-wider text-slate-500 text-[10px]">
                    Grid Coordinates
                  </th>
                  <th className="px-5 py-3.5 font-bold uppercase tracking-wider text-slate-500 text-[10px]">
                    Energy (FRP)
                  </th>
                  <th className="px-5 py-3.5 font-bold uppercase tracking-wider text-slate-500 text-[10px]">
                    Detected
                  </th>
                  <th className="px-5 py-3.5 font-bold uppercase tracking-wider text-slate-500 text-[10px]">
                    Status
                  </th>
                  <th className="px-5 py-3.5 text-right font-bold uppercase tracking-wider text-slate-500 text-[10px]">
                    Action
                  </th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-100">
                {filteredEvents.length === 0 && (
                  <tr>
                    <td colSpan={8} className="px-5 py-12 text-center text-slate-400">
                      No wildfire incidents match the selected filters.
                    </td>
                  </tr>
                )}
                {filteredEvents.map((event) => {
                  const triage = triageMap[event.id] || event.triage;
                  return (
                    <tr
                      key={event.id}
                      className="transition-colors hover:bg-slate-50/80 group"
                    >
                      <td className="px-5 py-3.5">
                        {triage ? (
                          <DangerBadge level={triage.danger_level} />
                        ) : (
                          <span className="text-[11px] text-slate-400">Pending</span>
                        )}
                      </td>
                      <td className="px-5 py-3.5">
                        {triage ? (
                          <ClassificationTag classification={triage.classification} />
                        ) : (
                          <span className="text-slate-400">—</span>
                        )}
                      </td>
                      <td className="px-5 py-3.5">
                        {triage ? (
                          <TriageSourceBadge source={triage.triage_source} />
                        ) : (
                          <span className="text-slate-400">—</span>
                        )}
                      </td>
                      <td className="px-5 py-3.5 font-mono font-semibold text-slate-800 tabular-nums">
                        {formatCoords(event.lat, event.lon)}
                      </td>
                      <td className="px-5 py-3.5 font-mono font-bold text-orange-600 tabular-nums">
                        {formatFRP(event.frp)}
                      </td>
                      <td className="px-5 py-3.5 text-slate-500 tabular-nums">
                        {formatDate(event.detected_at, 'dd MMM, HH:mm')}
                      </td>
                      <td className="px-5 py-3.5">
                        <StatusPill status={event.status} />
                      </td>
                      <td className="px-5 py-3.5 text-right">
                        <Link
                          href={`/events/${event.id}`}
                          className="inline-flex items-center gap-1 rounded-full bg-brand px-3 py-1 text-[11px] font-bold text-white shadow-sm transition-all hover:bg-brand-dark"
                        >
                          <span>Inspect</span>
                          <ExternalLink size={11} aria-hidden="true" />
                        </Link>
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>

          {/* Pagination Footer */}
          {totalPages > 1 && (
            <div className="flex items-center justify-between border-t border-edge bg-surface px-5 py-3.5 text-xs">
              <button
                onClick={() => setPage((p) => Math.max(1, p - 1))}
                disabled={page === 1}
                className={clsx(
                  'inline-flex items-center gap-1 rounded-full border px-3.5 py-1.5 font-semibold transition-colors',
                  page === 1
                    ? 'border-edge text-slate-300 cursor-not-allowed opacity-50'
                    : 'border-edge bg-white text-slate-700 hover:bg-slate-50'
                )}
              >
                <ChevronLeft size={13} aria-hidden="true" />
                Previous
              </button>
              <span className="text-slate-500 font-medium">
                Page <span className="text-slate-900 font-bold">{page}</span> of <span className="text-slate-900 font-bold">{totalPages}</span>
              </span>
              <button
                onClick={() => setPage((p) => Math.min(totalPages, p + 1))}
                disabled={page === totalPages}
                className={clsx(
                  'inline-flex items-center gap-1 rounded-full border px-3.5 py-1.5 font-semibold transition-colors',
                  page === totalPages
                    ? 'border-edge text-slate-300 cursor-not-allowed opacity-50'
                    : 'border-edge bg-white text-slate-700 hover:bg-slate-50'
                )}
              >
                Next
                <ChevronRight size={13} aria-hidden="true" />
              </button>
            </div>
          )}
        </div>
      )}
    </div>
  );
}

function StatusPill({ status }: { status: FireStatus }) {
  const classes: Record<FireStatus, string> = {
    PENDING: 'bg-amber-50 text-amber-700 border border-amber-200',
    TRIAGED: 'bg-orange-50 text-orange-700 border border-orange-200',
    ALERTED: 'bg-red-50 text-red-700 border border-red-200 shadow-sm animate-pulse',
    ARCHIVED: 'bg-slate-100 text-slate-600 border border-slate-200',
  };
  return (
    <span className={clsx('rounded-full px-2.5 py-0.5 text-[10px] font-bold uppercase tracking-wider', classes[status])}>
      {status}
    </span>
  );
}

