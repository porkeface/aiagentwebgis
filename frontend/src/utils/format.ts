/**
 * Display utilities for travel distances, durations, and transport modes.
 *
 * Single source of truth so the trip panel, map legend, and the right-side
 * itinerary always agree on units and rounding.
 */

export type TransportMode = 'walking' | 'driving' | 'transit';

/** Average urban speed (km/h) used for client-side duration estimation. */
export const MODE_SPEED_KMH: Readonly<Record<TransportMode, number>> = {
  walking: 5,
  driving: 30,
  transit: 20,
};

/** Display label + icon for each transport mode. */
export const MODE_META: Readonly<
  Record<TransportMode, { icon: string; label: string }>
> = {
  walking: { icon: '🚶', label: '步行' },
  driving: { icon: '🚗', label: '驾车' },
  transit: { icon: '🚌', label: '公交' },
};

/** Runtime type-guard. Backend JSON can carry any string for `mode`
 *  (e.g. legacy `"bicycling"`), so we narrow at the boundary instead of
 *  trusting the TypeScript union alone. */
export function isTransportMode(value: unknown): value is TransportMode {
  return value === 'walking' || value === 'driving' || value === 'transit';
}

/** Coerce an arbitrary string to a supported mode.
 *  Falls back to `defaultModeFor(km)` for unknown values, then `'driving'`. */
export function coerceMode(value: unknown, km: number): TransportMode {
  if (isTransportMode(value)) return value;
  return defaultModeFor(km);
}

/** Distance below which we render in metres, otherwise kilometres. */
const METRES_THRESHOLD_KM = 1;

/**
 * Format a distance in km.
 * < 1 km → "310m"; otherwise "1.5km".
 */
export function formatDistance(km: number): string {
  if (!Number.isFinite(km) || km < 0) return '—';
  if (km < METRES_THRESHOLD_KM) {
    return `${Math.round(km * 1000)}m`;
  }
  return `${km.toFixed(1)}km`;
}

/**
 * Format a duration in minutes.
 * < 1 min → "—"; < 60 min → "45 min"; exact hour → "2h"; otherwise "2h 5m".
 */
export function formatDuration(min: number): string {
  if (!Number.isFinite(min) || min < 1) return '—';
  const total = Math.round(min);
  if (total < 60) return `${total} min`;
  const h = Math.floor(total / 60);
  const m = total % 60;
  return m === 0 ? `${h}h` : `${h}h ${m}m`;
}

/**
 * Estimate travel time in minutes for `km` at the given mode's average speed.
 */
export function estimateDuration(km: number, mode: TransportMode): number {
  if (!Number.isFinite(km) || km <= 0) return 0;
  return Math.round((km / MODE_SPEED_KMH[mode]) * 60);
}

/**
 * Pick a sensible default mode when the backend didn't supply one.
 * Mirrors the backend's `WALK_THRESHOLD_KM = 2.0` rule
 * (see backend/agent/tools/submit_plan.py).
 */
export function defaultModeFor(km: number): TransportMode {
  return km < 2 ? 'walking' : 'driving';
}
