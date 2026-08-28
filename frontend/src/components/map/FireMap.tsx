'use client';

// IMPORTANT: This component must only be loaded via dynamic() with { ssr: false }
// in any Next.js page, as Leaflet requires browser APIs.
//
// Usage in page.tsx:
//   const FireMap = dynamic(() => import('@/components/map/FireMap').then(m => m.FireMap), { ssr: false });

import React, { useEffect } from 'react';
import { MapContainer, TileLayer, useMap } from 'react-leaflet';
import 'leaflet/dist/leaflet.css';

import {
  MAP_DEFAULT_CENTER,
  MAP_DEFAULT_ZOOM,
  OSM_TILE_URL,
  OSM_ATTRIBUTION,
} from '@/lib/constants';
import { FireMarker } from './FireMarker';
import { SpreadOverlay } from './SpreadOverlay';
import type { FireEvent } from '@/types/fire-event';
import type { Prediction } from '@/types/prediction';
import type { TriageReport } from '@/types/triage-report';

// ─── Leaflet default marker icon fix for Next.js ─────────────────────────────
// Webpack mangles the default icon URLs; replace them with CDN copies so no
// local PNG import is needed (avoids TS2307 errors with missing type declarations).
import L from 'leaflet';

// @ts-expect-error — _getIconUrl is not in Leaflet's public typings
delete L.Icon.Default.prototype._getIconUrl;
L.Icon.Default.mergeOptions({
  iconUrl: 'https://unpkg.com/leaflet@1.9.4/dist/images/marker-icon.png',
  iconRetinaUrl: 'https://unpkg.com/leaflet@1.9.4/dist/images/marker-icon-2x.png',
  shadowUrl: 'https://unpkg.com/leaflet@1.9.4/dist/images/marker-shadow.png',
});

// ─── Map bounds helper ────────────────────────────────────────────────────────

interface FitBoundsProps {
  events: FireEvent[];
}

interface FocusEventProps {
  event: FireEvent;
}

function FocusEvent({ event }: FocusEventProps) {
  const map = useMap();
  useEffect(() => {
    map.setView([event.lat, event.lon], 11, { animate: false });
  }, [event.lat, event.lon, map]);
  return null;
}

function FitBounds({ events }: FitBoundsProps) {
  const map = useMap();
  useEffect(() => {
    if (events.length === 0) return;
    const bounds = events.map((e) => [e.lat, e.lon] as [number, number]);
    map.fitBounds(bounds, { padding: [40, 40], maxZoom: 10 });
  }, [events, map]);
  return null;
}

// ─── FireMap component ────────────────────────────────────────────────────────

export interface FireMapProps {
  events: FireEvent[];
  triageMap?: Record<string, TriageReport>;
  predictionMap?: Record<string, Prediction>;
  selectedEventId?: string | null;
  onMarkerSelect: (eventId: string) => void;
}

/**
 * Main Leaflet fire event map.
 * - Base: OpenStreetMap tiles (no API key required)
 * - Default centre: Indonesia [0, 118], zoom 5
 * - Markers sized by FRP, colored by danger level
 * - Spread sector overlay when prediction data available
 * - MUST be loaded with dynamic() + { ssr: false }
 */
export function FireMap({
  events,
  triageMap = {},
  predictionMap = {},
  selectedEventId = null,
  onMarkerSelect,
}: FireMapProps) {
  return (
    <MapContainer
      center={MAP_DEFAULT_CENTER}
      zoom={MAP_DEFAULT_ZOOM}
      className="h-full w-full"
      data-testid="fire-map"
    >
      <TileLayer url={OSM_TILE_URL} attribution={OSM_ATTRIBUTION} />

      {events.length === 1 && <FocusEvent event={events[0]} />}
      {events.length > 1 && <FitBounds events={events} />}

      {events.map((event) => {
        const triage = triageMap[event.id] || event.triage;
        const prediction = predictionMap[event.id];
        return (
          // React.Fragment avoids invalid nesting — Leaflet layers must be
          // siblings inside MapContainer, not wrapped in a DOM element.
          <React.Fragment key={event.id}>
            <FireMarker
              event={event}
              triage={triage}
              isSelected={selectedEventId === event.id}
              onSelect={onMarkerSelect}
            />
            {prediction && (
              <SpreadOverlay
                lat={event.lat}
                lon={event.lon}
                prediction={prediction}
                visible={selectedEventId === event.id}
              />
            )}
          </React.Fragment>
        );
      })}
    </MapContainer>
  );
}
