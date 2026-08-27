'use client';

import Link from 'next/link';
import Image from 'next/image';
import dynamic from 'next/dynamic';
import { useTriageReport } from '@/hooks/useTriageReport';
import { usePrediction } from '@/hooks/usePrediction';
import { useFireEvent } from '@/hooks/useFireEvent';
import { DangerBadge } from '@/components/ui/DangerBadge';
import { ClassificationTag } from '@/components/ui/ClassificationTag';
import { TriageSourceBadge } from '@/components/ui/TriageSourceBadge';
import { LoadingSpinner } from '@/components/ui/LoadingSpinner';
import { ErrorAlert } from '@/components/ui/ErrorAlert';
import { SpreadRadiusChart } from '@/components/charts/SpreadRadiusChart';
import { ACTION_LABELS, ACTION_CLASSES } from '@/lib/constants';
import {
  formatDate,
  formatCoords,
  formatFRP,
  formatHectares,
  formatConfidence,
} from '@/lib/formatters';
import clsx from 'clsx';

const FireMap = dynamic(
  () => import('@/components/map/FireMap').then((m) => m.FireMap),
  { ssr: false, loading: () => <div className="h-64 bg-gray-100 rounded-xl animate-pulse" /> }
);

interface EventDetailPageProps {
  params: { id: string };
}

export default function EventDetailPage({ params }: EventDetailPageProps) {
  const { id } = params;

  const { data: event, isLoading: eventsLoading } = useFireEvent(id);

  const { data: triage, error: triageError } = useTriageReport(id);
  const { data: prediction } = usePrediction(id);

  if (eventsLoading) {
    return (
      <div className="flex h-full items-center justify-center">
        <LoadingSpinner size="lg" label="Loading event details…" />
      </div>
    );
  }

  if (!event) {
    return (
      <div className="mx-auto max-w-3xl px-4 py-12 text-center">
        <ErrorAlert message={`Event "${id}" not found.`} />
        <Link href="/events" className="mt-4 inline-block text-sm text-orange-600 hover:underline">
          ← Back to events
        </Link>
      </div>
    );
  }

  return (
    <div className="mx-auto min-h-full max-w-6xl space-y-5 px-4 py-5 pb-12 sm:px-6">
      {/* Breadcrumb */}
      <nav className="text-xs text-gray-400 flex items-center gap-1.5">
        <Link href="/" className="hover:text-gray-700">Dashboard</Link>
        <span>›</span>
        <Link href="/events" className="hover:text-gray-700">Events</Link>
        <span>›</span>
        <span className="text-gray-600 font-mono truncate max-w-xs">{id}</span>
      </nav>

      {/* Page header */}
      <div className="flex items-start justify-between gap-4 rounded-xl border border-slate-200 bg-white px-5 py-4 shadow-sm flex-wrap">
        <div>
          <p className="text-[11px] font-semibold uppercase tracking-[0.18em] text-orange-600">Detection detail</p>
          <h1 className="mt-1 text-2xl font-bold tracking-tight text-slate-900">Fire event</h1>
          <p className="mt-1 max-w-xs truncate font-mono text-xs text-slate-400 sm:max-w-md">{id}</p>
        </div>
        {triage && (
          <div className="flex items-center gap-2 flex-wrap">
            <DangerBadge level={triage.danger_level} showLabel />
            <ClassificationTag classification={triage.classification} />
            <TriageSourceBadge source={triage.triage_source} />
          </div>
        )}
      </div>

      <div className="grid grid-cols-1 gap-5 lg:grid-cols-[1.15fr_0.85fr]">
        {/* Left: map + satellite tile */}
        <div className="space-y-4">
          {/* Mini map */}
          <div className="h-[360px] overflow-hidden rounded-xl border border-slate-200 bg-slate-100 shadow-sm sm:h-[440px]">
            <FireMap
              events={[event]}
              triageMap={triage ? { [event.id]: triage } : {}}
              predictionMap={prediction ? { [event.id]: prediction } : {}}
              selectedEventId={id}
              onMarkerSelect={() => {}}
            />
          </div>

          {/* Satellite tile */}
          {event.tile_url ? (
            <div className="overflow-hidden rounded-xl border border-slate-200 bg-white shadow-sm">
              <Image
                src={`/api/proxy/tiles/${event.id}`}
                alt="Satellite tile"
                width={600}
                height={600}
                className="h-56 w-full object-cover sm:h-64"
                unoptimized
              />
              <p className="border-t border-gray-100 bg-slate-50 px-3 py-2 text-[11px] text-slate-500">
                NASA GIBS true-color imagery. Hotspot location is shown by the map marker.
              </p>
            </div>
          ) : (
            <div className="flex h-24 items-center justify-center rounded-xl border border-dashed border-gray-300 bg-gray-50 text-xs text-gray-400">
              No satellite tile
            </div>
          )}
        </div>

        {/* Right: event + triage details */}
        <div className="space-y-4">
          {/* Event info card */}
          <div className="rounded-xl border border-slate-200 bg-white p-5 shadow-sm space-y-2 text-sm">
            <h2 className="mb-3 text-xs font-semibold uppercase tracking-[0.16em] text-slate-500">
              Detection Info
            </h2>
            <Detail label="Location" value={formatCoords(event.lat, event.lon)} />
            <Detail label="Detected" value={formatDate(event.detected_at)} />
            <Detail label="Satellite" value={event.satellite} />
            <Detail label="FRP" value={formatFRP(event.frp)} />
            <Detail label="Status" value={event.status} />
            {event.alerted_at && (
              <Detail label="Alerted" value={formatDate(event.alerted_at)} />
            )}
          </div>

          {/* Triage card */}
          {triageError && <ErrorAlert message="Could not load triage report." />}
          {triage && (
            <div className="rounded-xl border border-slate-200 bg-white p-5 shadow-sm space-y-2 text-sm">
              <h2 className="text-xs font-semibold uppercase tracking-wide text-gray-500 mb-3">
                Triage Report
              </h2>
              <Detail label="Confidence" value={formatConfidence(triage.confidence)} />
              <Detail label="Fire area" value={formatHectares(triage.fire_area_ha)} />
              {triage.smoke_direction && (
                <Detail label="Smoke direction" value={triage.smoke_direction} />
              )}
              <Detail label="Processed" value={formatDate(triage.processed_at)} />
              <div className="pt-1">
                <span className="text-gray-500">Recommended: </span>
                <span className={clsx('px-2 py-0.5 rounded text-xs font-semibold', ACTION_CLASSES[triage.recommended_action])}>
                  {ACTION_LABELS[triage.recommended_action]}
                </span>
              </div>
              <p className="mt-2 text-sm text-gray-700 bg-gray-50 rounded-lg px-3 py-2 leading-relaxed">
                {triage.summary}
              </p>
            </div>
          )}

          {/* Prediction chart */}
          {prediction && (
            <div className="rounded-xl border border-slate-200 bg-white p-5 shadow-sm">
              <h2 className="text-xs font-semibold uppercase tracking-wide text-gray-500 mb-3">
                Spread Prediction
              </h2>
              <SpreadRadiusChart prediction={prediction} />
              <div className="mt-3 text-xs text-gray-400 space-y-0.5">
                <div>Wind: {prediction.wind_speed.toFixed(1)} m/s at {prediction.wind_direction}°</div>
                <div>Humidity: {prediction.humidity.toFixed(0)}%</div>
                <div>Model: {prediction.model_version}</div>
              </div>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}

function Detail({ label, value }: { label: string; value: string }) {
  return (
    <div className="flex gap-2">
      <span className="w-28 shrink-0 text-gray-400">{label}</span>
      <span className="text-gray-700 font-medium">{value}</span>
    </div>
  );
}
