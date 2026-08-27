import { format, parseISO, formatDistanceToNow } from 'date-fns';

/**
 * Format an ISO8601 datetime string for display.
 * Returns "N/A" if the value is null/undefined.
 */
export function formatDate(iso: string | null | undefined, pattern = 'dd MMM yyyy, HH:mm'): string {
  if (!iso) return 'N/A';
  try {
    return format(parseISO(iso), pattern);
  } catch {
    return iso;
  }
}

/**
 * Format an ISO8601 datetime string as relative time ("3 minutes ago").
 */
export function formatRelativeDate(iso: string | null | undefined): string {
  if (!iso) return 'N/A';
  try {
    return formatDistanceToNow(parseISO(iso), { addSuffix: true });
  } catch {
    return iso;
  }
}

/**
 * Format lat/lon coordinates to 4 decimal places.
 */
export function formatCoords(lat: number, lon: number): string {
  return `${lat.toFixed(4)}°, ${lon.toFixed(4)}°`;
}

/**
 * Format a fire area in hectares.
 * Returns "Unknown" if the value is null.
 */
export function formatHectares(ha: number | null): string {
  if (ha === null) return 'Unknown';
  if (ha >= 1000) return `${(ha / 1000).toFixed(1)}k ha`;
  return `${ha.toFixed(1)} ha`;
}

/**
 * Format a confidence value (0.0–1.0) as a percentage string.
 */
export function formatConfidence(confidence: number): string {
  return `${(confidence * 100).toFixed(0)}%`;
}

/**
 * Format Fire Radiative Power (MW) value.
 */
export function formatFRP(frp: number | null): string {
  if (frp === null) return 'N/A';
  return `${frp.toFixed(1)} MW`;
}
