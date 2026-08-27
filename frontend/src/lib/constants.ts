import type { Classification } from '@/types/triage-report';

// ─── Danger Level ────────────────────────────────────────────────────────────

/** Hex colours for fire marker circles and badges, indexed 1–5. */
export const DANGER_COLORS: Record<number, string> = {
  1: '#22C55E',
  2: '#FACC15',
  3: '#FB923C',
  4: '#EF4444',
  5: '#991B1B',
};

/** Tailwind class pairs (bg + text) for DangerBadge, indexed 1–5. */
export const DANGER_BADGE_CLASSES: Record<number, string> = {
  1: 'bg-green-500 text-white',
  2: 'bg-yellow-400 text-yellow-950',
  3: 'bg-orange-400 text-white',
  4: 'bg-red-500 text-white',
  5: 'bg-red-900 text-white',
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

/** Tailwind class pairs for ClassificationTag, per classification type. */
export const CLASSIFICATION_CLASSES: Record<Classification, string> = {
  CONFIRMED_FIRE: 'bg-red-100 text-red-800 border-red-300',
  PROBABLE_FIRE: 'bg-orange-100 text-orange-800 border-orange-300',
  FALSE_POSITIVE: 'bg-green-100 text-green-800 border-green-300',
  INDUSTRIAL_SOURCE: 'bg-blue-100 text-blue-800 border-blue-300',
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

/** Tailwind class pairs for action pills. */
export const ACTION_CLASSES: Record<string, string> = {
  MONITOR: 'bg-slate-100 text-slate-700',
  DISPATCH: 'bg-orange-100 text-orange-800',
  DISPATCH_LOCAL: 'bg-orange-100 text-orange-800',
  DISPATCH_REGIONAL: 'bg-red-100 text-red-800',
  EVACUATE: 'bg-red-100 text-red-800',
  INVESTIGATE: 'bg-yellow-100 text-yellow-800',
};

// ─── Map ──────────────────────────────────────────────────────────────────────

/** Default map centre: Indonesia centroid. */
export const MAP_DEFAULT_CENTER: [number, number] = [
  parseFloat(process.env.NEXT_PUBLIC_MAP_CENTER_LAT ?? '0'),
  parseFloat(process.env.NEXT_PUBLIC_MAP_CENTER_LON ?? '118'),
];

export const MAP_DEFAULT_ZOOM = 5;

/** OSM tile URL template — no API key required. */
export const OSM_TILE_URL = 'https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png';
export const OSM_ATTRIBUTION =
  '&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors';

// ─── Polling ──────────────────────────────────────────────────────────────────

/** SWR polling interval for fire events — 5 minutes. */
export const EVENTS_POLL_INTERVAL_MS = 5 * 60 * 1000;
