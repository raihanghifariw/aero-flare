'use client';

import Link from 'next/link';
import Image from 'next/image';
import dynamic from 'next/dynamic';
import clsx from 'clsx';
import {
  ChevronRight,
  Satellite,
  Crosshair,
  Wind,
  Droplets,
  ArrowLeft,
} from 'lucide-react';
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

const FireMap = dynamic(
  () => import('@/components/map/FireMap').then((m) => m.FireMap),
  {
    ssr: false,
    loading: () => (
      <div className="h-64 flex items-center justify-center rounded-2xl bg-surface-raised border border-edge sm:h-[440px]">
        <LoadingSpinner label="Loading satellite coordinates…" showText />
      </div>
    ),
  }
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
      <div className="flex h-full items-center justify-center bg-surface">
        <LoadingSpinner size="lg" label="Retrieving incident telemetry…" showText />
      </div>
    );
  }

  if (!event) {
    return (
      <div className="mx-auto max-w-2xl px-4 py-16 text-center">
        <ErrorAlert message={`Incident record "${id}" not found in telemetry registry.`} />
        <Link
          href="/events"
          className="mt-6 inline-flex items-center gap-2 rounded-full border border-edge bg-white px-5 py-2.5 text-xs font-bold text-brand shadow-sm hover:bg-slate-50"
        >
          <ArrowLeft size={14} aria-hidden="true" />
          Return to Incidents Explorer
        </Link>
      </div>
    );
  }

  return (
    <div className="mx-auto min-h-full max-w-7xl space-y-6 px-4 py-6 pb-16 sm:px-6">
      {/* Breadcrumb Navigation */}
      <nav className="flex items-center gap-2 text-xs text-slate-500 font-medium" aria-label="Breadcrumb">
        <Link href="/" className="transition-colors hover:text-brand">Command Center</Link>
        <ChevronRight size={13} aria-hidden="true" />
        <Link href="/events" className="transition-colors hover:text-brand">Incidents Explorer</Link>
        <ChevronRight size={13} aria-hidden="true" />
        <span className="max-w-xs truncate text-brand font-bold">{id}</span>
      </nav>

      {/* Hero Header Card */}
      <div className="flex flex-wrap items-center justify-between gap-4 rounded-2xl border border-edge bg-surface-raised p-6 shadow-sm">
        <div className="space-y-1">
          <div className="flex items-center gap-2">
            <span className="flex h-7 w-7 items-center justify-center rounded-xl bg-brand/10 text-brand">
              <Crosshair size={16} aria-hidden="true" />
            </span>
            <span className="text-[11px] font-bold uppercase tracking-wider text-brand">
              Incident Telemetry Inspector
            </span>
          </div>
          <h1 className="font-mono text-2xl font-black tracking-tight text-ink">
            {formatCoords(event.lat, event.lon)}
          </h1>
          <p className="text-xs text-slate-500 font-medium">
            Record ID: <span className="font-mono text-slate-700 font-bold">{id}</span> · Detected {formatDate(event.detected_at, 'dd MMM yyyy, HH:mm:ss')}
          </p>
        </div>

        {/* Status & Badges */}
        {triage && (
          <div className="flex flex-wrap items-center gap-2">
            <DangerBadge level={triage.danger_level} showLabel />
            <ClassificationTag classification={triage.classification} />
            <TriageSourceBadge source={triage.triage_source} />
          </div>
        )}
      </div>

      {/* Main Split Telemetry Grid */}
      <div className="grid grid-cols-1 gap-6 lg:grid-cols-[1.15fr_0.85fr]">
        {/* Left Column: Tactical Map & NASA GIBS Tile */}
        <div className="space-y-5">
          {/* Tactical Vector Map */}
          <div className="h-[360px] overflow-hidden rounded-2xl border border-edge shadow-sm sm:h-[440px]">
            <FireMap
              events={[event]}
              triageMap={triage ? { [event.id]: triage } : {}}
              predictionMap={prediction ? { [event.id]: prediction } : {}}
              selectedEventId={id}
              onMarkerSelect={() => {}}
            />
          </div>

          {/* NASA Satellite Optical Tile Card */}
          {event.tile_url ? (
            <div className="overflow-hidden rounded-2xl border border-edge bg-slate-900 shadow-sm">
              <div className="relative">
                <Image
                  src={`/api/proxy/tiles/${event.id}`}
                  alt="Satellite tile"
                  width={600}
                  height={600}
                  className="h-56 w-full object-cover sm:h-64"
                  unoptimized
                />
                <div className="pointer-events-none absolute inset-0 flex items-center justify-center">
                  <div className="h-10 w-10 rounded-full border border-red-500/80 bg-red-500/10 shadow-[0_0_12px_rgba(239,68,68,0.8)] animate-pulse" />
                  <div className="absolute h-14 w-[1px] bg-red-500/60" />
                  <div className="absolute w-14 h-[1px] bg-red-500/60" />
                </div>
                <div className="absolute bottom-2 right-2 rounded-full bg-black/75 px-3 py-0.5 font-mono text-[9px] text-white backdrop-blur">
                  NASA GIBS 250m TRUE-COLOR
                </div>
              </div>
              <div className="flex items-center justify-between border-t border-edge bg-surface-raised px-4 py-3 text-xs text-slate-500 font-medium">
                <span className="flex items-center gap-1.5 text-slate-700">
                  <Satellite size={13} className="text-brand" aria-hidden="true" />
                  {event.satellite} Sensor Payload
                </span>
                <span className="font-bold text-orange-600 font-mono">FRP: {formatFRP(event.frp)}</span>
              </div>
            </div>
          ) : (
            <div className="flex h-28 items-center justify-center rounded-2xl border border-dashed border-edge bg-surface-raised text-xs text-slate-400">
              No optical satellite imagery available
            </div>
          )}
        </div>

        {/* Right Column: Telemetry Specs & Spread Predictions */}
        <div className="space-y-5">
          {/* Telemetry Sensor Specs Card */}
          <div className="space-y-3.5 rounded-2xl border border-edge bg-surface-raised p-6 shadow-sm">
            <h2 className="text-[11px] font-bold uppercase tracking-wider text-brand">
              Detection Telemetry
            </h2>
            <div className="grid grid-cols-2 gap-2.5 text-xs">
              <DetailBox label="Latitude / Longitude" value={formatCoords(event.lat, event.lon)} />
              <DetailBox label="Radiative Power" value={formatFRP(event.frp)} highlight />
              <DetailBox label="Sensor Satellite" value={event.satellite} />
              <DetailBox label="Detection Status" value={event.status} />
              <DetailBox label="Timestamp" value={formatDate(event.detected_at, 'dd MMM, HH:mm')} />
              {event.alerted_at && (
                <DetailBox label="Alert Dispatched" value={formatDate(event.alerted_at, 'dd MMM, HH:mm')} />
              )}
            </div>
          </div>

          {/* AI Multimodal Triage Card */}
          {triageError && <ErrorAlert message="Could not load AI triage telemetry report." />}
          {triage && (
            <div className="space-y-3.5 rounded-2xl border border-edge bg-surface-raised p-6 shadow-sm">
              <h2 className="text-[11px] font-bold uppercase tracking-wider text-brand">
                AI Multimodal Triage Assessment
              </h2>

              <div className="grid grid-cols-2 gap-2.5 text-xs">
                <DetailBox label="VLM Confidence" value={formatConfidence(triage.confidence)} />
                <DetailBox label="Estimated Area" value={formatHectares(triage.fire_area_ha)} />
                {triage.smoke_direction && (
                  <DetailBox label="Smoke Plume Vector" value={triage.smoke_direction} />
                )}
                <DetailBox label="Analysis Time" value={formatDate(triage.processed_at, 'HH:mm:ss')} />
              </div>

              {/* Recommended Command Action Banner */}
              <div
                className={clsx(
                  'rounded-2xl p-4 text-xs shadow-sm border',
                  ACTION_CLASSES[triage.recommended_action]
                )}
              >
                <span className="block text-[9px] font-bold uppercase tracking-wider opacity-80">
                  Recommended Command Action
                </span>
                <span className="mt-0.5 block text-sm font-black">
                  {ACTION_LABELS[triage.recommended_action]}
                </span>
              </div>

              <div className="rounded-2xl border border-edge bg-surface p-4 text-xs leading-relaxed text-slate-600">
                <span className="block text-[9px] uppercase font-bold text-slate-400 mb-1">
                  VLM Narrative Assessment
                </span>
                <p>{triage.summary}</p>
              </div>
            </div>
          )}

          {/* Spread Prediction Radar Card */}
          {prediction && (
            <div className="space-y-3.5 rounded-2xl border border-edge bg-surface-raised p-6 shadow-sm">
              <h2 className="text-[11px] font-bold uppercase tracking-wider text-brand">
                Fire Perimeter Spread Prediction
              </h2>
              <SpreadRadiusChart prediction={prediction} />

              <div className="grid grid-cols-2 gap-2.5 text-xs">
                <div className="flex items-center gap-2.5 rounded-2xl border border-edge bg-surface p-3 shadow-sm">
                  <Wind size={15} className="text-brand shrink-0" aria-hidden="true" />
                  <div>
                    <span className="block text-[9px] uppercase font-medium text-slate-400">Surface Wind</span>
                    <span className="font-bold font-mono text-slate-900 tabular-nums">
                      {prediction.wind_speed.toFixed(1)} m/s ({prediction.wind_direction}°)
                    </span>
                  </div>
                </div>

                <div className="flex items-center gap-2.5 rounded-2xl border border-edge bg-surface p-3 shadow-sm">
                  <Droplets size={15} className="text-brand shrink-0" aria-hidden="true" />
                  <div>
                    <span className="block text-[9px] uppercase font-medium text-slate-400">Humidity</span>
                    <span className="font-bold font-mono text-slate-900 tabular-nums">
                      {prediction.humidity.toFixed(0)}%
                    </span>
                  </div>
                </div>
              </div>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}

function DetailBox({ label, value, highlight = false }: { label: string; value: string; highlight?: boolean }) {
  return (
    <div className="rounded-2xl border border-edge bg-surface p-3 shadow-sm">
      <span className="block text-[9px] uppercase tracking-wider text-slate-400 font-medium">{label}</span>
      <span className={clsx('mt-1 block font-mono font-bold tabular-nums', highlight ? 'text-orange-600' : 'text-slate-800')}>
        {value}
      </span>
    </div>
  );
}

