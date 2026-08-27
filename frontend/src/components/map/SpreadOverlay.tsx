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
 * Semi-transparent sector polygon showing the predicted fire spread direction and
 * 6h / 12h / 24h radii.
 * Only rendered when `visible` is true (i.e. the parent event is selected).
 */
export function SpreadOverlay({ lat, lon, prediction, visible = false }: SpreadOverlayProps) {
  if (!visible) return null;

  const { spread_direction_deg, radius_6h_km, radius_12h_km, radius_24h_km } = prediction;

  // Build three concentric arc sectors (±45° around spread direction)
  function sectorPoints(radiusKm: number): [number, number][] {
    const halfArc = 45; // ±45° sector
    const steps = 12;
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
      {/* 24h — lightest, outermost */}
      <Polygon
        positions={sectorPoints(radius_24h_km)}
        pathOptions={{ color: '#EF4444', fillColor: '#EF4444', fillOpacity: 0.08, weight: 1 }}
      />
      {/* 12h */}
      <Polygon
        positions={sectorPoints(radius_12h_km)}
        pathOptions={{ color: '#FB923C', fillColor: '#FB923C', fillOpacity: 0.12, weight: 1 }}
      />
      {/* 6h — densest, innermost */}
      <Polygon
        positions={sectorPoints(radius_6h_km)}
        pathOptions={{ color: '#FCD34D', fillColor: '#FCD34D', fillOpacity: 0.2, weight: 1.5 }}
      />
    </>
  );
}
