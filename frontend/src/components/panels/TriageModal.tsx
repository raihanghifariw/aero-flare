'use client';

import { useEffect } from 'react';
import Image from 'next/image';
import clsx from 'clsx';
import { DangerBadge } from '@/components/ui/DangerBadge';
import { ClassificationTag } from '@/components/ui/ClassificationTag';
import { TriageSourceBadge } from '@/components/ui/TriageSourceBadge';
import { LoadingSpinner } from '@/components/ui/LoadingSpinner';
import { ErrorAlert } from '@/components/ui/ErrorAlert';
import { SpreadRadiusChart } from '@/components/charts/SpreadRadiusChart';
import { formatDate, formatHectares, formatConfidence, formatCoords } from '@/lib/formatters';
import { ACTION_LABELS, ACTION_CLASSES } from '@/lib/constants';
import { useTriageReport } from '@/hooks/useTriageReport';
import { usePrediction } from '@/hooks/usePrediction';
import type { FireEvent } from '@/types/fire-event';

export interface TriageModalProps {
  event: FireEvent | null;
  onClose: () => void;
}

/**
 * Triage detail panel.
 * - Mobile: bottom sheet (fixed bottom, full width)
 * - Desktop: right-side drawer
 * Loads triage + prediction data on demand via SWR.
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
        className="fixed inset-0 z-40 bg-black/30 md:hidden"
        onClick={onClose}
        aria-hidden="true"
      />

      {/* Panel */}
      <div
        data-testid="triage-modal"
        role="dialog"
        aria-modal="true"
        aria-label="Triage Report"
        className={clsx(
          'fixed z-50 bg-white shadow-2xl overflow-y-auto',
          // Mobile: bottom sheet
          'bottom-0 left-0 right-0 max-h-[80vh] rounded-t-2xl',
          // Desktop: right drawer
          'md:bottom-0 md:top-0 md:left-auto md:right-0 md:max-h-full md:w-96 md:rounded-none'
        )}
      >
        {/* Header */}
        <div className="sticky top-0 flex items-center justify-between border-b border-gray-200 bg-white px-4 py-3 z-10">
          <div>
            <h2 className="text-sm font-semibold text-gray-800">Triage Report</h2>
            <p className="mt-0.5 text-[11px] text-gray-400">
              {formatCoords(event.lat, event.lon)}
            </p>
          </div>
          <button
            onClick={onClose}
            aria-label="Close triage panel"
            className="rounded p-1 text-gray-400 hover:text-gray-700 hover:bg-gray-100"
          >
            ✕
          </button>
        </div>

        <div className="px-4 py-4 space-y-4">
          {/* Satellite tile */}
          {event.tile_url && (
            <div className="overflow-hidden rounded-lg border border-gray-200">
              <Image
                src={`/api/proxy/tiles/${event.id}`}
                alt={`Satellite tile for event ${event.id}`}
                width={400}
                height={400}
                className="h-48 w-full object-cover"
                unoptimized // presigned R2 URLs change — disable Next.js cache
              />
              <p className="border-t border-gray-100 bg-slate-50 px-3 py-2 text-[11px] text-slate-500">
                NASA GIBS true-color imagery. Use the marker location as the hotspot reference.
              </p>
            </div>
          )}
          {!event.tile_url && (
            <div className="flex h-24 items-center justify-center rounded-lg border border-dashed border-gray-300 bg-gray-50 px-4 text-center text-xs text-gray-400">
              {isPending ? 'Satellite tile is being prepared' : 'No satellite tile available'}
            </div>
          )}

          {/* Event coordinates + timestamp */}
          <div className="text-xs text-gray-500 space-y-0.5">
            <div>
              <span className="font-medium text-gray-700">Location:</span>{' '}
              {formatCoords(event.lat, event.lon)}
            </div>
            <div>
              <span className="font-medium text-gray-700">Detected:</span>{' '}
              {formatDate(event.detected_at)}
            </div>
            <div>
              <span className="font-medium text-gray-700">Satellite:</span> {event.satellite}
            </div>
          </div>

          {/* Loading / error states */}
          {triageLoading && <LoadingSpinner label="Loading triage report…" />}
          {triageError && !isPending && (
            <ErrorAlert message="Could not load triage report for this event." />
          )}
          {isPending && !triage && (
            <div className="rounded-lg border border-amber-200 bg-amber-50 px-3 py-3 text-sm text-amber-900">
              <p className="font-semibold">Analysis pending</p>
              <p className="mt-1 text-xs leading-relaxed text-amber-800">
                This detection is queued for tile download and triage. The level and report will appear automatically when processing finishes.
              </p>
            </div>
          )}

          {/* Triage report */}
          {triage && (
            <div className="space-y-3">
              {/* Source badge */}
              <div className="flex items-center gap-2">
                <TriageSourceBadge source={triage.triage_source} />
                <span className="text-xs text-gray-400">
                  {formatDate(triage.processed_at)}
                </span>
              </div>

              {/* Classification + confidence */}
              <div className="flex items-center gap-2 flex-wrap">
                <ClassificationTag classification={triage.classification} />
                <span className="text-xs text-gray-500">
                  {formatConfidence(triage.confidence)} confidence
                </span>
              </div>

              {/* Danger level */}
              <div className="flex items-center gap-2">
                <DangerBadge level={triage.danger_level} showLabel />
              </div>

              {/* Summary */}
              <p className="text-sm text-gray-700 leading-relaxed bg-gray-50 rounded-lg px-3 py-2">
                {triage.summary}
              </p>

              {/* Recommended action */}
              <div>
                <span className="text-xs text-gray-500 font-medium">Recommended Action: </span>
                <span
                  className={clsx(
                    'inline-block px-2 py-0.5 rounded text-xs font-semibold',
                    ACTION_CLASSES[triage.recommended_action]
                  )}
                >
                  {ACTION_LABELS[triage.recommended_action]}
                </span>
              </div>

              {/* Fire area */}
              <div className="text-xs text-gray-600">
                <span className="font-medium">Estimated area:</span>{' '}
                <span className={triage.fire_area_ha === null ? 'text-gray-400 italic' : 'text-gray-700'}>
                  {formatHectares(triage.fire_area_ha)}
                </span>
              </div>

              {/* Smoke direction */}
              {triage.smoke_direction && (
                <div className="text-xs text-gray-600">
                  <span className="font-medium">Smoke direction:</span>{' '}
                  {triage.smoke_direction}
                </div>
              )}
            </div>
          )}

          {/* Spread prediction chart */}
          {prediction && (
            <div className="rounded-lg border border-gray-200 p-3">
              <SpreadRadiusChart prediction={prediction} />
              <div className="mt-2 text-xs text-gray-400 space-y-0.5">
                <div>Wind: {prediction.wind_speed.toFixed(1)} m/s at {prediction.wind_direction}°</div>
                <div>Humidity: {prediction.humidity.toFixed(0)}%</div>
              </div>
            </div>
          )}
        </div>
      </div>
    </>
  );
}
