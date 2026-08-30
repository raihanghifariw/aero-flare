'use client';

import { Polygon } from 'react-leaflet';
import type { Prediction } from '@/types/prediction';

export interface SpreadOverlayProps {
  lat: number;
  lon: number;
  prediction: Prediction;
  visible?: boolean;
}

const DEG_TO_RAD = Math.PI / 180;
const KM_PER_DEG_LAT = 111.32; // approximate

/**
 * Convert a bearing (degrees from north) + distance (km) to a [lat, lon] offset.
 */
function bearingToLatLon(
  originLat: number,
  originLon: number,
  bearingDeg: number,
  distanceKm: number
): [number, number] {
  const latKm = KM_PER_DEG_LAT;
  const lonKm = KM_PER_DEG_LAT * Math.cos(originLat * DEG_TO_RAD);

  const deltaLat = (Math.cos(bearingDeg * DEG_TO_RAD) * distanceKm) / latKm;
  const deltaLon = (Math.sin(bearingDeg * DEG_TO_RAD) * distanceKm) / lonKm;

  return [originLat + deltaLat, originLon + deltaLon];
}

/**
 * Tactical sector polygon showing the predicted wildfire spread vector and
 * 6h / 12h / 24h expansion radii.
 */
export function SpreadOverlay({ lat, lon, prediction, visible = false }: SpreadOverlayProps) {
  if (!visible) return null;

  const { spread_direction_deg, radius_6h_km, radius_12h_km, radius_24h_km } = prediction;

  // Build concentric arc sectors (±45° around spread direction)
  function sectorPoints(radiusKm: number): [number, number][] {
    const halfArc = 45;
    const steps = 16;
    const points: [number, number][] = [[lat, lon]];
    for (let i = 0; i <= steps; i++) {
      const bearing = spread_direction_deg - halfArc + (i * (halfArc * 2)) / steps;
      points.push(bearingToLatLon(lat, lon, bearing, radiusKm));
    }
    points.push([lat, lon]);
    return points;
  }

  return (
    <>
      {/* 24h Horizon — Outermost Sector */}
      <Polygon
        positions={sectorPoints(radius_24h_km)}
        pathOptions={{
          color: '#DC2626',
          fillColor: '#EF4444',
          fillOpacity: 0.12,
          weight: 1.5,
          dashArray: '4 4',
        }}
      />
      {/* 12h Horizon */}
      <Polygon
        positions={sectorPoints(radius_12h_km)}
        pathOptions={{
          color: '#EA580C',
          fillColor: '#FB923C',
          fillOpacity: 0.18,
          weight: 1.5,
          dashArray: '3 3',
        }}
      />
      {/* 6h Horizon — Immediate Danger Zone */}
      <Polygon
        positions={sectorPoints(radius_6h_km)}
        pathOptions={{
          color: '#D97706',
          fillColor: '#F59E0B',
          fillOpacity: 0.28,
          weight: 2,
        }}
      />
    </>
  );
}
