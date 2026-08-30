'use client';

import { useEffect } from 'react';
import Link from 'next/link';
import Image from 'next/image';
import clsx from 'clsx';
import {
  Cloud,
  Satellite,
  X,
  Crosshair,
  Wind,
  Droplets,
  AlertTriangle,
  ExternalLink,
} from 'lucide-react';

import { DangerBadge } from '@/components/ui/DangerBadge';
import { ClassificationTag } from '@/components/ui/ClassificationTag';
import { TriageSourceBadge } from '@/components/ui/TriageSourceBadge';
import { LoadingSpinner } from '@/components/ui/LoadingSpinner';
import { ErrorAlert } from '@/components/ui/ErrorAlert';
import { SpreadRadiusChart } from '@/components/charts/SpreadRadiusChart';
import { formatDate, formatHectares, formatConfidence, formatCoords, formatFRP } from '@/lib/formatters';
import { ACTION_LABELS, ACTION_CLASSES } from '@/lib/constants';
import { useTriageReport } from '@/hooks/useTriageReport';
import { usePrediction } from '@/hooks/usePrediction';
import type { FireEvent } from '@/types/fire-event';

export interface TriageModalProps {
  event: FireEvent | null;
  onClose: () => void;
}

/**
 * Modern Triage & Incident Telemetry Inspector Drawer.
 * - Mobile: Modern bottom sheet
 * - Desktop: Command right-side inspector panel
 */
export function TriageModal({ event, onClose }: TriageModalProps) {
  const { data: triage, isLoading: triageLoading, error: triageError } = useTriageReport(
    event?.id ?? null
  );
  const { data: prediction } = usePrediction(event?.id ?? null);

  // Close on Escape key
  useEffect(() => {
    function handleKey(e: KeyboardEvent) {
      if (e.key === 'Escape') onClose();
    }
    window.addEventListener('keydown', handleKey);
    return () => window.removeEventListener('keydown', handleKey);
  }, [onClose]);

  if (!event) return null;
  const isPending = event.status === 'PENDING';

  return (
    <>
      {/* Backdrop (mobile) */}
      <div
        className="fixed inset-0 z-40 bg-slate-900/40 backdrop-blur-sm md:hidden"
        onClick={onClose}
        aria-hidden="true"
      />

      {/* Modern Inspector Panel */}
      <div
        data-testid="triage-modal"
        role="dialog"
        aria-modal="true"
        aria-label="Triage Report"
        className={clsx(
          'fixed z-50 overflow-y-auto border-edge bg-surface-raised shadow-2xl transition-transform',
          // Mobile: bottom sheet
          'bottom-0 left-0 right-0 max-h-[85vh] rounded-t-3xl border-t',
          // Desktop: right telemetry drawer
          'md:bottom-0 md:top-0 md:left-auto md:right-0 md:max-h-full md:w-[28rem] md:rounded-none md:border-l md:border-t-0'
        )}
      >
        {/* Header HUD */}
        <div className="sticky top-0 z-10 flex items-center justify-between border-b border-edge bg-surface-raised/95 px-5 py-4 backdrop-blur shadow-sm">
          <div className="flex items-center gap-3">
            <div className="flex h-8 w-8 items-center justify-center rounded-xl bg-brand/10 text-brand">
              <Crosshair size={18} aria-hidden="true" />
            </div>
            <div>
              <h2 className="text-xs font-bold uppercase tracking-wider text-ink">
                Hotspot Telemetry & Triage
              </h2>
              <p className="font-mono text-xs text-brand font-bold tabular-nums">
                {formatCoords(event.lat, event.lon)}
              </p>
            </div>
          </div>
          <button
            onClick={onClose}
            aria-label="Close triage panel"
            className="rounded-full border border-edge bg-surface-overlay p-2 text-slate-500 transition-colors hover:bg-slate-200 hover:text-slate-900"
          >
            <X size={16} aria-hidden="true" />
          </button>
        </div>

        <div className="space-y-4 p-5">
          {/* Satellite Imagery Tile Card */}
          <div className="relative overflow-hidden rounded-2xl border border-edge bg-slate-900 shadow-card">
            {event.tile_url ? (
              <div className="group relative">
                <Image
                  src={`/api/proxy/tiles/${event.id}`}
                  alt={`Satellite tile for event ${event.id}`}
                  width={400}
                  height={400}
                  className="h-48 w-full object-cover transition-transform group-hover:scale-105"
                  unoptimized
                />
                {/* Optical HUD Crosshair Overlays */}
                <div className="pointer-events-none absolute inset-0 flex items-center justify-center">
                  <div className="h-8 w-8 rounded-full border border-red-500/80 bg-red-500/10 shadow-[0_0_12px_rgba(239,68,68,0.8)] animate-pulse" />
                  <div className="absolute h-12 w-[1px] bg-red-500/60" />
                  <div className="absolute w-12 h-[1px] bg-red-500/60" />
                </div>
                <div className="absolute bottom-2 right-2 rounded-full bg-black/75 px-2.5 py-0.5 font-mono text-[9px] text-white backdrop-blur">
                  NASA GIBS 250m TRUE-COLOR
                </div>
              </div>
            ) : (
              <div className="flex h-32 flex-col items-center justify-center border border-dashed border-edge bg-slate-50 p-4 text-center">
                <Satellite size={20} className="text-slate-400 mb-1.5" aria-hidden="true" />
                <span className="text-xs font-medium text-slate-600">
                  {isPending ? 'Satellite tile pipeline synthesizing…' : 'No optical satellite tile available'}
                </span>
              </div>
            )}
            <div className="flex items-center justify-between border-t border-edge bg-surface-raised px-4 py-2.5 text-[11px] text-slate-500 font-medium">
              <span className="flex items-center gap-1.5 text-slate-700">
                <Satellite size={13} className="text-brand" aria-hidden="true" />
                {event.satellite} SENSOR
              </span>
              <span className="tabular-nums font-bold text-orange-600 font-mono">
                FRP: {formatFRP(event.frp)}
              </span>
            </div>
          </div>

          {/* Detections Meta Summary Grid */}
          <div className="grid grid-cols-2 gap-2.5 text-xs">
            <div className="rounded-2xl border border-edge bg-surface p-3 shadow-sm">
              <span className="block text-[10px] font-medium uppercase tracking-wider text-slate-400">Detected Timestamp</span>
              <span className="mt-1 block font-semibold text-slate-800">
                {formatDate(event.detected_at, 'dd MMM yyyy, HH:mm')}
              </span>
            </div>
            <div className="rounded-2xl border border-edge bg-surface p-3 shadow-sm">
              <span className="block text-[10px] font-medium uppercase tracking-wider text-slate-400">Incident Status</span>
              <span className="mt-1 block font-bold text-slate-900">
                {event.status}
              </span>
            </div>
          </div>

          {/* Loading & Error Indicators */}
          {triageLoading && <LoadingSpinner label="Running VLM Triage Analysis…" showText />}
          {triageError && !isPending && (
            <ErrorAlert message="Could not load AI triage report for this event." />
          )}
          {isPending && !triage && (
            <div className="rounded-2xl border border-amber-200 bg-amber-50 p-4 text-amber-900 shadow-sm">
              <div className="flex items-center gap-2 text-xs font-bold text-amber-800">
                <AlertTriangle size={15} aria-hidden="true" />
                <span>Multimodal Triage Queued</span>
              </div>
              <p className="mt-1.5 text-xs leading-relaxed text-amber-800/80">
                This hotspot is queued for vision model inference. Danger classification and perimeter assessment will update automatically upon completion.
              </p>
            </div>
          )}

          {/* Triage Assessment Results */}
          {triage && (
            <div className="space-y-3.5">
              {/* Classification Hero Card */}
              <div className="rounded-2xl border border-edge bg-surface p-4 space-y-3 shadow-sm">
                <div className="flex items-center justify-between gap-2 border-b border-edge/60 pb-2.5">
                  <ClassificationTag classification={triage.classification} />
                  <span className="font-mono text-xs font-bold text-brand tabular-nums">
                    {formatConfidence(triage.confidence)} Confidence
                  </span>
                </div>

                <div className="flex items-center justify-between gap-2">
                  <DangerBadge level={triage.danger_level} showLabel />
                  <TriageSourceBadge source={triage.triage_source} />
                </div>

                <div className="flex items-center justify-between text-[11px] text-slate-500 font-medium pt-1">
                  <span>Processed: {formatDate(triage.processed_at, 'HH:mm:ss')}</span>
                  <span>Est. Area: {formatHectares(triage.fire_area_ha)}</span>
                </div>
              </div>

              {/* Recommended Action Tactical Banner */}
              <div
                className={clsx(
                  'rounded-2xl border p-4 text-sm shadow-sm',
                  ACTION_CLASSES[triage.recommended_action]
                )}
              >
                <span className="block text-[10px] font-bold uppercase tracking-wider opacity-80">
                  Recommended Command Action
                </span>
                <span className="mt-0.5 block text-base font-extrabold tracking-tight">
                  {ACTION_LABELS[triage.recommended_action]}
                </span>
              </div>

              {/* Cloud Obscuration Alert */}
              {triage.visually_obscured && (
                <div className="rounded-2xl border border-amber-200 bg-amber-50 p-3.5 text-xs text-amber-900">
                  <div className="flex items-center gap-1.5 font-bold text-amber-800">
                    <Cloud size={15} aria-hidden="true" />
                    <span>Cloud Obscuration Fusion</span>
                  </div>
                  <p className="mt-1 leading-relaxed text-amber-800/80">
                    Optical imagery is obscured ({triage.cloud_cover_percent ? `${triage.cloud_cover_percent.toFixed(0)}%` : '50%+'}). FIRMS thermal telemetry indicates active energy ({event.frp ?? 'Elevated'} MW). Priority maintained via infrared sensor fusion.
                  </p>
                </div>
              )}

              {/* Executive Summary */}
              <div className="rounded-2xl border border-edge bg-surface p-4 text-xs leading-relaxed text-slate-600 shadow-sm">
                <span className="block text-[10px] font-bold uppercase tracking-wider text-slate-400 mb-1.5">
                  VLM Incident Summary
                </span>
                <p>{triage.summary}</p>
              </div>

              {/* Spread Prediction Radar HUD */}
              {prediction && (
                <div className="space-y-2.5">
                  <SpreadRadiusChart prediction={prediction} />

                  {/* Weather Telemetry Chips */}
                  <div className="grid grid-cols-2 gap-2 text-xs">
                    <div className="flex items-center gap-2.5 rounded-2xl border border-edge bg-surface p-2.5 text-slate-600 shadow-sm">
                      <Wind size={15} className="text-brand shrink-0" aria-hidden="true" />
                      <div>
                        <span className="block text-[9px] uppercase font-medium text-slate-400">Surface Wind</span>
                        <span className="font-bold font-mono text-slate-900 tabular-nums">
                          {prediction.wind_speed.toFixed(1)} m/s ({prediction.wind_direction}°)
                        </span>
                      </div>
                    </div>

                    <div className="flex items-center gap-2.5 rounded-2xl border border-edge bg-surface p-2.5 text-slate-600 shadow-sm">
                      <Droplets size={15} className="text-brand shrink-0" aria-hidden="true" />
                      <div>
                        <span className="block text-[9px] uppercase font-medium text-slate-400">Rel. Humidity</span>
                        <span className="font-bold font-mono text-slate-900 tabular-nums">
                          {prediction.humidity.toFixed(0)}%
                        </span>
                      </div>
                    </div>
                  </div>
                </div>
              )}
            </div>
          )}

          {/* Full Page Dossier Action */}
          <div className="pt-2 border-t border-edge">
            <Link
              href={`/events/${event.id}`}
              className="flex w-full items-center justify-center gap-2 rounded-full border border-brand/20 bg-brand/5 px-4 py-2.5 text-xs font-bold text-brand shadow-sm transition-all hover:bg-brand hover:text-white"
            >
              <span>Open Dedicated Incident Page</span>
              <ExternalLink size={13} aria-hidden="true" />
            </Link>
          </div>
        </div>
      </div>
    </>
  );
}


