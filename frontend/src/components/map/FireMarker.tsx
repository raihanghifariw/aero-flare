'use client';

import { CircleMarker, Popup } from 'react-leaflet';
import { DANGER_COLORS } from '@/lib/constants';
import { ClassificationTag } from '@/components/ui/ClassificationTag';
import { DangerBadge } from '@/components/ui/DangerBadge';
import { TriageSourceBadge } from '@/components/ui/TriageSourceBadge';
import { formatDate, formatCoords, formatFRP } from '@/lib/formatters';
import type { FireEvent } from '@/types/fire-event';
import type { TriageReport } from '@/types/triage-report';

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
 * Circle marker representing a single fire event on the Leaflet map.
 * - Color driven by triage danger_level (1–5) or fallback orange.
 * - VLM triage → solid fill; RULE_BASED_FALLBACK → dashed stroke.
 * - Clicking the marker calls onSelect(event.id).
 */
export function FireMarker({ event, triage, isSelected = false, onSelect }: FireMarkerProps) {
  const dangerLevel = triage?.danger_level;
  const isAlerted = event.status === 'ALERTED';
  const color = dangerLevel ? DANGER_COLORS[dangerLevel] : isAlerted ? '#DC2626' : '#9CA3AF';
  const isRuleBased = triage?.triage_source === 'RULE_BASED_FALLBACK';
  const radius = markerRadius(event.frp);

  const pathOptions = {
    color: isAlerted ? '#DC2626' : color,
    fillColor: color,
    fillOpacity: isSelected ? 0.95 : triage ? (isAlerted ? 0.85 : 0.6) : 0.45,
    weight: isAlerted ? 3 : isRuleBased ? 2 : 1.5,
    dashArray: triage ? (isRuleBased && !isAlerted ? '4 4' : undefined) : '2 4',
    opacity: 1,
  };

  return (
    <>
      {/* Outer halo ring for ALERTED or Level 4/5 Critical Events */}
      {(isAlerted || (dangerLevel && dangerLevel >= 4)) && (
        <CircleMarker
          center={[event.lat, event.lon]}
          radius={radius + 7}
          pathOptions={{
            color: '#DC2626',
            fillColor: '#EF4444',
            fillOpacity: 0.25,
            weight: 2,
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
        <Popup>
          <div className="min-w-[180px] text-sm">
            <div className="mb-1 flex items-center gap-1.5 flex-wrap">
              {isAlerted && (
                <span className="rounded bg-red-600 px-1.5 py-0.5 text-[10px] font-bold text-white uppercase tracking-wider">
                  🚨 ALERTED
                </span>
              )}
              {triage && <DangerBadge level={triage.danger_level} />}
              {triage && <ClassificationTag classification={triage.classification} />}
            </div>
            {triage && (
              <div className="mb-1">
                <TriageSourceBadge source={triage.triage_source} />
              </div>
            )}
            <div className="text-xs text-gray-600 space-y-0.5">
              <div>
                <span className="font-medium">Location:</span> {formatCoords(event.lat, event.lon)}
              </div>
              <div>
                <span className="font-medium">FRP:</span> {formatFRP(event.frp)}
              </div>
              <div>
                <span className="font-medium">Detected:</span> {formatDate(event.detected_at)}
              </div>
              <div>
                <span className="font-medium">Satellite:</span> {event.satellite}
              </div>
            </div>
            <button
              className="mt-2 w-full rounded bg-orange-500 px-2 py-1 text-xs text-white hover:bg-orange-600 transition-colors"
              onClick={() => onSelect(event.id)}
            >
              View Triage Report →
            </button>
          </div>
        </Popup>
      </CircleMarker>
    </>
  );
}
