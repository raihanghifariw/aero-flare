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
  const color = dangerLevel ? DANGER_COLORS[dangerLevel] : '#9CA3AF';
  const isRuleBased = triage?.triage_source === 'RULE_BASED_FALLBACK';

  const pathOptions = {
    color,
    fillColor: color,
    fillOpacity: isSelected ? 0.9 : triage ? 0.6 : 0.45,
    weight: isRuleBased ? 2 : 1.5,
    dashArray: triage ? (isRuleBased ? '4 4' : undefined) : '2 4',
    opacity: 1,
  };

  return (
    <CircleMarker
      center={[event.lat, event.lon]}
      radius={markerRadius(event.frp)}
      pathOptions={pathOptions}
      eventHandlers={{ click: () => onSelect(event.id) }}
      data-testid="fire-marker"
    >
      <Popup>
        <div className="min-w-[180px] text-sm">
          <div className="mb-1 flex items-center gap-1.5">
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
  );
}
