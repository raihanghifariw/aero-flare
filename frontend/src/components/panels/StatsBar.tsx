'use client';

import clsx from 'clsx';
import { Flame, Activity, Clock } from 'lucide-react';
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
 * Modern SaaS top stats telemetry HUD bar:
 * Shows live pipeline metrics, confirmed fires, telemetry health, and last sensor pass.
 */
export function StatsBar({ stats, isLoading = false }: StatsBarProps) {
  const eventsCount = stats?.events_today ?? 0;
  const confirmedCount = stats?.confirmed_fires_today ?? 0;
  const isHealthy = stats?.pipeline_healthy ?? true;

  return (
    <header className="flex items-center gap-3 border-b border-edge bg-surface px-4 py-2.5 overflow-x-auto select-none">
      {/* 48h Events Metric */}
      <div className="flex items-center gap-3 rounded-2xl border border-edge bg-surface-raised px-3.5 py-1.5 shadow-sm shrink-0">
        <div className="flex h-8 w-8 items-center justify-center rounded-xl bg-brand/10 text-brand">
          <Activity size={16} aria-hidden="true" />
        </div>
        <div className="flex flex-col">
          <div className="flex items-baseline gap-1.5">
            <span className="font-mono text-lg font-black leading-none tabular-nums text-ink">
              {isLoading ? '…' : String(eventsCount)}
            </span>
            <span className="text-[10px] font-semibold text-brand tracking-wide">HOTSPOTS</span>
          </div>
          <span className="text-[10px] font-medium text-ink-muted">
            Events (48h)
          </span>
        </div>
      </div>

      {/* Confirmed Fires Metric */}
      <div className="flex items-center gap-3 rounded-2xl border border-edge bg-surface-raised px-3.5 py-1.5 shadow-sm shrink-0">
        <div className="relative flex h-8 w-8 items-center justify-center rounded-xl bg-red-50 text-red-600">
          <Flame size={16} aria-hidden="true" />
          {confirmedCount > 0 && !isLoading && (
            <span className="absolute -right-0.5 -top-0.5 h-2 w-2 rounded-full bg-red-500 animate-ping-slow" />
          )}
        </div>
        <div className="flex flex-col">
          <div className="flex items-baseline gap-1.5">
            <span className="font-mono text-lg font-black leading-none tabular-nums text-red-600">
              {isLoading ? '…' : String(confirmedCount)}
            </span>
            <span className="text-[10px] font-semibold text-red-600/80 tracking-wide">ACTIVE</span>
          </div>
          <span className="text-[10px] font-medium text-ink-muted">
            Confirmed fires
          </span>
        </div>
      </div>

      {/* Last Ingestion Update */}
      <div className="hidden sm:flex items-center gap-3 rounded-2xl border border-edge bg-surface-raised px-3.5 py-1.5 shadow-sm shrink-0">
        <div className="flex h-8 w-8 items-center justify-center rounded-xl bg-surface-overlay text-ink-muted">
          <Clock size={16} aria-hidden="true" />
        </div>
        <div className="flex flex-col">
          <span className="text-xs font-semibold leading-tight text-ink tabular-nums">
            {isLoading ? '…' : formatRelativeDate(stats?.last_ingestion_at ?? null)}
          </span>
          <span className="text-[10px] font-medium text-ink-muted">
            Last updated
          </span>
        </div>
      </div>

      {/* Pipeline Status Indicator */}
      <div className="ml-auto flex items-center gap-2.5 rounded-full border border-edge bg-surface-raised px-3 py-1.5 shadow-sm shrink-0">
        <div
          className={clsx(
            'flex h-6 w-6 items-center justify-center rounded-full transition-colors',
            isLoading
              ? 'bg-slate-100 text-ink-faint'
              : isHealthy
              ? 'bg-emerald-50 text-emerald-600'
              : 'bg-red-50 text-red-600'
          )}
        >
          <span
            className={clsx(
              'h-2 w-2 rounded-full',
              isLoading
                ? 'bg-ink-faint'
                : isHealthy
                ? 'bg-emerald-500 animate-pulse'
                : 'bg-red-500 animate-ping-slow'
            )}
            aria-hidden="true"
          />
        </div>
        <div className="flex flex-col pr-1">
          <span
            className={clsx(
              'text-xs font-bold leading-tight tracking-tight',
              isLoading ? 'text-ink-faint' : isHealthy ? 'text-emerald-700' : 'text-red-700'
            )}
            role="status"
            aria-label={isHealthy ? 'Pipeline healthy' : 'Pipeline error'}
          >
            {isLoading ? 'Checking…' : isHealthy ? 'Pipeline OK' : 'Pipeline Error'}
          </span>
          <span className="text-[9px] font-medium text-ink-faint">TELEMETRY INGESTION</span>
        </div>
      </div>
    </header>
  );
}

