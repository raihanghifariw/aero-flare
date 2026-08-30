import type { Classification } from '@/types/triage-report';

// ─── Danger Level ────────────────────────────────────────────────────────────

/** Hex colours for fire marker circles and badges, indexed 1–5. */
export const DANGER_COLORS: Record<number, string> = {
  1: '#10B981', // emerald minimal
  2: '#F59E0B', // amber low
  3: '#FB923C', // orange moderate
  4: '#EF4444', // red high
  5: '#DC2626', // deep crimson critical
};

/** Text colour (hex) paired with each danger level for legible badges. */
export const DANGER_TEXT_COLORS: Record<number, string> = {
  1: '#065F46',
  2: '#92400E',
  3: '#9A3412',
  4: '#991B1B',
  5: '#FFFFFF',
};

/** Human-readable labels for danger levels. */
export const DANGER_LABELS: Record<number, string> = {
  1: 'Minimal',
  2: 'Low',
  3: 'Moderate',
  4: 'High',
  5: 'Critical',
};

// ─── Classification ───────────────────────────────────────────────────────────

/** Human-readable display labels for classification values. */
export const CLASSIFICATION_LABELS: Record<Classification, string> = {
  CONFIRMED_FIRE: 'Confirmed Fire',
  PROBABLE_FIRE: 'Probable Fire',
  FALSE_POSITIVE: 'False Positive',
  INDUSTRIAL_SOURCE: 'Industrial Source',
};

/** Tailwind class pairs for ClassificationTag, per classification type (modern SaaS). */
export const CLASSIFICATION_CLASSES: Record<Classification, string> = {
  CONFIRMED_FIRE: 'bg-red-50 text-red-700 border-red-200',
  PROBABLE_FIRE: 'bg-orange-50 text-orange-700 border-orange-200',
  FALSE_POSITIVE: 'bg-emerald-50 text-emerald-700 border-emerald-200',
  INDUSTRIAL_SOURCE: 'bg-sky-50 text-sky-700 border-sky-200',
};

// ─── Recommended Action ───────────────────────────────────────────────────────

/** Human-readable display labels for recommended actions. */
export const ACTION_LABELS: Record<string, string> = {
  MONITOR: 'Monitor',
  DISPATCH: 'Dispatch Units',
  DISPATCH_LOCAL: 'Dispatch Local',
  DISPATCH_REGIONAL: 'Dispatch Regional',
  EVACUATE: 'Evacuate Area',
  INVESTIGATE: 'Investigate',
};

/** Tailwind class pairs for action pills (modern SaaS). */
export const ACTION_CLASSES: Record<string, string> = {
  MONITOR: 'bg-slate-100 text-slate-700 border-slate-200',
  DISPATCH: 'bg-orange-50 text-orange-700 border-orange-200 shadow-sm',
  DISPATCH_LOCAL: 'bg-orange-50 text-orange-700 border-orange-200 shadow-sm',
  DISPATCH_REGIONAL: 'bg-red-50 text-red-700 border-red-200 shadow-sm',
  EVACUATE: 'bg-red-600 text-white border-red-700 shadow-md animate-pulse-subtle',
  INVESTIGATE: 'bg-amber-50 text-amber-700 border-amber-200',
};

// ─── Map & Cartography ────────────────────────────────────────────────────────

/** Default map centre: Indonesia centroid. */
export const MAP_DEFAULT_CENTER: [number, number] = [
  parseFloat(process.env.NEXT_PUBLIC_MAP_CENTER_LAT ?? '0.7893'),
  parseFloat(process.env.NEXT_PUBLIC_MAP_CENTER_LON ?? '113.9213'),
];

export const MAP_DEFAULT_ZOOM = 5;

/** Base Tile Layers */
export const MAP_LAYERS = {
  VOYAGER: {
    id: 'voyager',
    name: 'Carto Voyager (Clean)',
    url: 'https://{s}.basemaps.cartocdn.com/rastertiles/voyager/{z}/{x}/{y}{r}.png',
    attribution: '&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors &copy; <a href="https://carto.com/attributions">CARTO</a>',
  },
  LIGHT: {
    id: 'light',
    name: 'Positron Light',
    url: 'https://{s}.basemaps.cartocdn.com/light_all/{z}/{x}/{y}{r}.png',
    attribution: '&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors &copy; <a href="https://carto.com/attributions">CARTO</a>',
  },
  SATELLITE: {
    id: 'satellite',
    name: 'Satellite Hybrid',
    url: 'https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}',
    attribution: 'Tiles &copy; Esri &mdash; Source: Esri, i-cubed, USDA, USGS, AEX, GeoEye, Getmapping, Aerogrid, IGN, IGP, UPR-EGP, and the GIS User Community',
  },
  DARK: {
    id: 'dark',
    name: 'Dark Mode',
    url: 'https://{s}.basemaps.cartocdn.com/dark_all/{z}/{x}/{y}{r}.png',
    attribution: '&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors &copy; <a href="https://carto.com/attributions">CARTO</a>',
  },
} as const;

export const OSM_TILE_URL = MAP_LAYERS.VOYAGER.url;
export const OSM_ATTRIBUTION = MAP_LAYERS.VOYAGER.attribution;

/** Indonesian Regional Presets for fast map jump */
export const INDONESIA_REGIONS = [
  { id: 'all', name: 'All Indonesia', center: [0.7893, 113.9213] as [number, number], zoom: 5 },
  { id: 'kalimantan', name: 'Kalimantan', center: [-0.2, 114.0] as [number, number], zoom: 6 },
  { id: 'sumatra', name: 'Sumatra', center: [0.5, 101.5] as [number, number], zoom: 6 },
  { id: 'sulawesi', name: 'Sulawesi', center: [-1.5, 120.5] as [number, number], zoom: 6 },
  { id: 'papua', name: 'Papua', center: [-4.0, 138.0] as [number, number], zoom: 6 },
  { id: 'jawa', name: 'Jawa & Bali', center: [-7.5, 110.5] as [number, number], zoom: 7 },
] as const;

// ─── Polling ──────────────────────────────────────────────────────────────────

/** SWR polling interval for fire events — 5 minutes. */
export const EVENTS_POLL_INTERVAL_MS = 5 * 60 * 1000;


