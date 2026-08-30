'use client';

import Link from 'next/link';
import { CircleMarker, Popup } from 'react-leaflet';
import { DANGER_COLORS } from '@/lib/constants';
import { ClassificationTag } from '@/components/ui/ClassificationTag';
import { DangerBadge } from '@/components/ui/DangerBadge';
import { TriageSourceBadge } from '@/components/ui/TriageSourceBadge';
import { formatDate, formatCoords, formatFRP } from '@/lib/formatters';
import type { FireEvent } from '@/types/fire-event';
import type { TriageReport } from '@/types/triage-report';
import { Satellite, Zap, Compass, ExternalLink } from 'lucide-react';



export interface FireMarkerProps {
  event: FireEvent;
  triage?: TriageReport;
  isSelected?: boolean;
  onSelect: (eventId: string) => void;
}

/** Radius of the circle marker in pixels, scaled by FRP (Fire Radiative Power). */
function markerRadius(frp: number | null): number {
  if (frp === null) return 8;
  // Scale: 1 MW → 8px, 500 MW → 24px, capped at 32px
  return Math.min(8 + Math.sqrt(frp) * 0.7, 32);
}

/**
 * Circle marker representing a single wildfire detection on the Leaflet map.
 * - Color driven by triage danger_level (1–5) or alert red.
 * - VLM triage → solid fill; RULE_BASED_FALLBACK → dashed stroke.
 */
export function FireMarker({ event, triage, isSelected = false, onSelect }: FireMarkerProps) {
  const dangerLevel = triage?.danger_level;
  const isAlerted = event.status === 'ALERTED';
  const color = dangerLevel ? DANGER_COLORS[dangerLevel] : isAlerted ? '#DC2626' : '#FF5722';
  const isRuleBased = triage?.triage_source === 'RULE_BASED_FALLBACK';
  const radius = markerRadius(event.frp);

  const pathOptions = {
    color: isSelected ? '#1877F2' : isAlerted ? '#EF4444' : color,
    fillColor: color,
    fillOpacity: isSelected ? 0.95 : triage ? (isAlerted ? 0.85 : 0.7) : 0.55,
    weight: isSelected ? 3.5 : isAlerted ? 2.5 : isRuleBased ? 2 : 1.5,
    dashArray: triage ? (isRuleBased && !isAlerted ? '4 4' : undefined) : '2 4',
    opacity: 1,
  };

  return (
    <>
      {/* Outer beacon halo ring for Alerted or Level 4/5 Critical Events */}
      {(isAlerted || (dangerLevel && dangerLevel >= 4)) && (
        <CircleMarker
          center={[event.lat, event.lon]}
          radius={radius + 8}
          pathOptions={{
            color: '#EF4444',
            fillColor: '#EF4444',
            fillOpacity: 0.15,
            weight: 1.5,
            dashArray: '3 3',
          }}
          interactive={false}
        />
      )}
      <CircleMarker
        center={[event.lat, event.lon]}
        radius={radius}
        pathOptions={pathOptions}
        eventHandlers={{ click: () => onSelect(event.id) }}
        data-testid="fire-marker"
      >
        <Popup className="saas-popup">
          <div className="min-w-[220px] max-w-[260px] text-xs font-sans">
            {/* Header badges */}
            <div className="mb-2 flex flex-wrap items-center justify-between gap-1.5 border-b border-slate-100 pb-2">
              <div className="flex items-center gap-1.5">
                {isAlerted && (
                  <span className="flex items-center gap-1 rounded-full bg-red-100 px-2 py-0.5 text-[9px] font-bold uppercase tracking-wider text-red-700">
                    <span className="h-1.5 w-1.5 rounded-full bg-red-500 animate-pulse" />
                    Alerted
                  </span>
                )}
                {triage && <DangerBadge level={triage.danger_level} />}
              </div>
              {triage && <TriageSourceBadge source={triage.triage_source} />}
            </div>

            {triage && (
              <div className="mb-2.5">
                <ClassificationTag classification={triage.classification} />
              </div>
            )}

            {/* Telemetry Metrics */}
            <div className="space-y-1.5 rounded-xl bg-slate-50 p-2.5 text-[11px] border border-slate-100">
              <div className="flex items-center justify-between text-slate-600">
                <span className="flex items-center gap-1 text-slate-400">
                  <Compass size={11} className="text-brand" aria-hidden="true" />
                  Grid
                </span>
                <span className="font-mono text-slate-900 font-semibold tabular-nums">
                  {formatCoords(event.lat, event.lon)}
                </span>
              </div>

              <div className="flex items-center justify-between text-slate-600">
                <span className="flex items-center gap-1 text-slate-400">
                  <Zap size={11} className="text-orange-500" aria-hidden="true" />
                  Energy (FRP)
                </span>
                <span className="font-mono text-orange-600 font-bold tabular-nums">
                  {formatFRP(event.frp)}
                </span>
              </div>

              <div className="flex items-center justify-between text-slate-600">
                <span className="flex items-center gap-1 text-slate-400">
                  <Satellite size={11} className="text-slate-400" aria-hidden="true" />
                  Sensor
                </span>
                <span className="font-medium text-slate-700">{event.satellite}</span>
              </div>

              <div className="pt-0.5 text-[10px] text-slate-400">
                Detected: {formatDate(event.detected_at, 'dd MMM yyyy, HH:mm')}
              </div>
            </div>

            <Link
              href={`/events/${event.id}`}
              className="mt-2.5 flex w-full items-center justify-center gap-1.5 rounded-full bg-brand px-3 py-1.5 text-xs font-bold text-white shadow-sm transition-all hover:bg-brand-dark"
            >
              <span>Inspect Full Incident Dossier</span>
              <ExternalLink size={12} aria-hidden="true" />
            </Link>
          </div>
        </Popup>
      </CircleMarker>
    </>
  );
}


