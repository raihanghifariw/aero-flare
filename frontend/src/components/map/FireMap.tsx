'use client';

// IMPORTANT: This component must only be loaded via dynamic() with { ssr: false }
// in any Next.js page, as Leaflet requires browser APIs.

import React, { useEffect, useState } from 'react';
import { MapContainer, TileLayer, useMap } from 'react-leaflet';
import 'leaflet/dist/leaflet.css';
import { Layers, LocateFixed, Globe2 } from 'lucide-react';

import {
  MAP_DEFAULT_CENTER,
  MAP_DEFAULT_ZOOM,
  MAP_LAYERS,
  INDONESIA_REGIONS,
} from '@/lib/constants';
import { FireMarker } from './FireMarker';
import { SpreadOverlay } from './SpreadOverlay';
import type { FireEvent } from '@/types/fire-event';
import type { Prediction } from '@/types/prediction';
import type { TriageReport } from '@/types/triage-report';

// ─── Leaflet default marker icon fix for Next.js ─────────────────────────────
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

function MapController({ targetCenter, targetZoom }: { targetCenter: [number, number] | null; targetZoom: number | null }) {
  const map = useMap();
  useEffect(() => {
    if (targetCenter && targetZoom !== null) {
      map.flyTo(targetCenter, targetZoom, { duration: 1.2 });
    }
  }, [targetCenter, targetZoom, map]);
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

type LayerKey = keyof typeof MAP_LAYERS;

/**
 * Main Leaflet wildfire map.
 * - Base: CartoDB Voyager / Positron clean light tiles
 * - Layer switcher: Clean Voyager / Positron / Satellite Hybrid / Dark Mode
 * - Indonesian regional quick-jump controls
 */
export function FireMap({
  events,
  triageMap = {},
  predictionMap = {},
  selectedEventId = null,
  onMarkerSelect,
}: FireMapProps) {
  const [activeLayer, setActiveLayer] = useState<LayerKey>('VOYAGER');
  const [layerMenuOpen, setLayerMenuOpen] = useState(false);
  const [targetView, setTargetView] = useState<{ center: [number, number]; zoom: number } | null>(null);

  const currentTileConfig = MAP_LAYERS[activeLayer] || MAP_LAYERS.VOYAGER;

  return (
    <div className="relative h-full w-full">
      <MapContainer
        center={MAP_DEFAULT_CENTER}
        zoom={MAP_DEFAULT_ZOOM}
        className="h-full w-full"
        data-testid="fire-map"
      >
        <TileLayer
          key={currentTileConfig.url}
          url={currentTileConfig.url}
          attribution={currentTileConfig.attribution}
          maxZoom={19}
        />

        {events.length === 1 && <FocusEvent event={events[0]} />}
        {events.length > 1 && !targetView && <FitBounds events={events} />}
        <MapController targetCenter={targetView?.center ?? null} targetZoom={targetView?.zoom ?? null} />

        {events.map((event) => {
          const triage = triageMap[event.id] || event.triage;
          const prediction = predictionMap[event.id];
          return (
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

      {/* Map Layer & Region Controls (Bottom-Left) */}
      <div className="pointer-events-auto absolute bottom-4 left-4 z-[400] flex flex-wrap items-center gap-2">
        {/* Layer Selector */}
        <div className="relative">
          <button
            onClick={() => setLayerMenuOpen(!layerMenuOpen)}
            className="flex items-center gap-1.5 rounded-full border border-edge bg-white px-3 py-1.5 text-xs font-semibold text-ink shadow-md backdrop-blur transition-colors hover:bg-slate-50"
            title="Switch Map Tile Layer"
          >
            <Layers size={13} className="text-brand" aria-hidden="true" />
            <span className="hidden sm:inline">{currentTileConfig.name}</span>
          </button>

          {layerMenuOpen && (
            <div className="absolute bottom-full mb-2 left-0 flex flex-col gap-1 rounded-2xl border border-edge bg-white p-1.5 shadow-xl min-w-[170px]">
              {(Object.keys(MAP_LAYERS) as LayerKey[]).map((key) => (
                <button
                  key={key}
                  onClick={() => {
                    setActiveLayer(key);
                    setLayerMenuOpen(false);
                  }}
                  className={`flex items-center justify-between rounded-xl px-3 py-1.5 text-left text-xs font-medium transition-colors ${
                    activeLayer === key
                      ? 'bg-brand/10 text-brand font-bold'
                      : 'text-ink-muted hover:bg-slate-50 hover:text-ink'
                  }`}
                >
                  <span>{MAP_LAYERS[key].name}</span>
                  {activeLayer === key && <span className="h-1.5 w-1.5 rounded-full bg-brand" />}
                </button>
              ))}
            </div>
          )}
        </div>

        {/* Region Fast Jump */}
        <div className="hidden lg:flex items-center gap-1 rounded-full border border-edge bg-white px-3 py-1 shadow-md">
          <Globe2 size={13} className="text-brand mr-1" aria-hidden="true" />
          {INDONESIA_REGIONS.map((region) => (
            <button
              key={region.id}
              onClick={() => setTargetView({ center: region.center, zoom: region.zoom })}
              className="rounded-full px-2 py-0.5 text-[11px] font-medium text-ink-muted transition-colors hover:bg-slate-100 hover:text-ink"
            >
              {region.name}
            </button>
          ))}
        </div>

        {/* Recenter Button */}
        <button
          onClick={() => setTargetView({ center: MAP_DEFAULT_CENTER, zoom: MAP_DEFAULT_ZOOM })}
          className="flex h-8 w-8 items-center justify-center rounded-full border border-edge bg-white text-ink-muted shadow-md transition-colors hover:bg-slate-50 hover:text-ink"
          title="Reset to Indonesia View"
        >
          <LocateFixed size={14} aria-hidden="true" />
        </button>
      </div>
    </div>
  );
}

