'use client';

import clsx from 'clsx';
import { formatRelativeDate } from '@/lib/formatters';

export interface PipelineStats {
  events_today: number;
  confirmed_fires_today: number;
  last_ingestion_at: string | null;
  pipeline_healthy: boolean;
}

export interface StatsBarProps {
  stats?: PipelineStats | null;
  isLoading?: boolean;
}

/**
 * Top stats bar showing live pipeline summary:
 * total events today, confirmed fires, last update time, pipeline health indicator.
 */
export function StatsBar({ stats, isLoading = false }: StatsBarProps) {
  return (
    <header className="flex items-center gap-2 border-b border-slate-200 bg-white px-4 py-2.5 text-sm overflow-x-auto">
      <Stat
        label="Events (48h)"
        value={isLoading ? '…' : String(stats?.events_today ?? 0)}
      />
      <div className="hidden h-7 w-px bg-slate-200 shrink-0 sm:block" />
      <Stat
        label="Confirmed fires"
        value={isLoading ? '…' : String(stats?.confirmed_fires_today ?? 0)}
        valueClass="text-red-600 font-bold"
      />
      <div className="hidden h-7 w-px bg-slate-200 shrink-0 sm:block" />
      <Stat
        label="Last updated"
        value={isLoading ? '…' : formatRelativeDate(stats?.last_ingestion_at ?? null)}
      />
      <div className="ml-auto flex items-center gap-1.5 shrink-0">
        <span
          className={clsx(
            'h-2 w-2 rounded-full',
            isLoading
              ? 'bg-gray-300'
              : stats?.pipeline_healthy
              ? 'bg-green-500'
              : 'bg-red-500'
          )}
          aria-label={stats?.pipeline_healthy ? 'Pipeline healthy' : 'Pipeline error'}
        />
        <span className="text-xs text-gray-500">
          {isLoading ? 'Checking…' : stats?.pipeline_healthy ? 'Pipeline OK' : 'Pipeline Error'}
        </span>
      </div>
    </header>
  );
}

interface StatProps {
  label: string;
  value: string;
  valueClass?: string;
}

function Stat({ label, value, valueClass }: StatProps) {
  return (
    <div className="flex min-w-[112px] items-baseline gap-1.5 rounded-lg border border-slate-200 bg-slate-50 px-2.5 py-1.5 shrink-0">
      <span className={clsx('text-base font-bold tabular-nums text-slate-900', valueClass)}>
        {value}
      </span>
      <span className="text-xs text-gray-400">{label}</span>
    </div>
  );
}
