/**
 * Amap client-side direction service — fetches real road paths for a single
 * POI→POI segment in the selected transport mode.
 *
 * Wraps AMap.Driving, AMap.Walking, and AMap.Transfer behind a single unified
 * function so the trip panel's per-segment mode switcher can query the real
 * polyline without the backend.
 */

import { getAMap } from '@/utils/amap'
import type { TransportMode } from '@/utils/format'

export interface SegmentRouteResult {
  polyline: string   // encoded polyline string "lng,lat;lng,lat;..."
  distance: number   // km
  duration: number   // minutes
  mode: TransportMode
}

/**
 * Fetch a real-roads route for a single POI→POI leg in the requested mode.
 *
 * @param origin      [lng, lat] of the starting POI
 * @param destination [lng, lat] of the ending POI
 * @param mode        'driving' | 'walking' | 'transit'
 *
 * @returns Route data with polyline, or null on failure.
 */
export async function fetchSegmentRoute(
  origin: [number, number],
  destination: [number, number],
  mode: TransportMode,
): Promise<SegmentRouteResult | null> {
  const AMap = getAMap()
  if (!AMap) return null

  try {
    if (mode === 'walking') {
      return await _walkingRoute(AMap, origin, destination)
    }
    if (mode === 'driving') {
      return await _drivingRoute(AMap, origin, destination)
    }
    // transit (bus/subway)
    return await _transitRoute(AMap, origin, destination)
  } catch {
    return null
  }
}

// ── Private helpers ────────────────────────────────────────────────────────

function _drivingRoute(
  AMap: typeof AMap,
  origin: [number, number],
  destination: [number, number],
): Promise<SegmentRouteResult | null> {
  return new Promise((resolve) => {
    const driving = new AMap.Driving({ policy: AMap.DrivingPolicy.LEAST_TIME })
    driving.search(
      new AMap.LngLat(origin[0], origin[1]),
      new AMap.LngLat(destination[0], destination[1]),
      (status: string, result: unknown) => {
        try { driving.destroy?.() } catch { /* best-effort */ }

        if (status !== 'complete') return resolve(null)

        const r = result as {
          routes?: Array<{
            distance: number
            time?: number           // seconds — AMap Driving returns `time`
            duration?: number        // some versions use `duration`
            steps?: Array<{ path: AMap.LngLat[] }>
          }>
        }
        const route = r.routes?.[0]
        if (!route) return resolve(null)

        const polyline = _encodePolyline(route)
        const distance = route.distance / 1000  // metres → km
        // AMap Driving returns `time` (seconds) on most v2 SDK versions.
        const seconds = route.time ?? route.duration ?? 0
        const duration = seconds > 0 ? seconds / 60 : distance * 2.5

        resolve({
          polyline,
          distance: Math.round(distance * 100) / 100,
          duration: Math.round(duration),
          mode: 'driving',
        })
      },
    )
  })
}

function _walkingRoute(
  AMap: typeof AMap,
  origin: [number, number],
  destination: [number, number],
): Promise<SegmentRouteResult | null> {
  return new Promise((resolve) => {
    const walking = new AMap.Walking({})
    walking.search(
      new AMap.LngLat(origin[0], origin[1]),
      new AMap.LngLat(destination[0], destination[1]),
      (status: string, result: unknown) => {
        try { walking.destroy?.() } catch { /* best-effort */ }

        if (status !== 'complete') return resolve(null)

        const r = result as {
          routes?: Array<{ distance: number; duration: number; steps?: Array<{ path: AMap.LngLat[] }> }>
        }
        const route = r.routes?.[0]
        if (!route) return resolve(null)

        const polyline = _encodePolyline(route)
        const distance = route.distance / 1000
        const duration = route.duration / 60    // seconds → minutes

        resolve({
          polyline,
          distance: Math.round(distance * 100) / 100,
          duration: Math.round(duration),
          mode: 'walking',
        })
      },
    )
  })
}

function _transitRoute(
  AMap: typeof AMap,
  origin: [number, number],
  destination: [number, number],
): Promise<SegmentRouteResult | null> {
  return new Promise((resolve) => {
    const transfer = new AMap.Transfer({
      city: 'auto',
      policy: AMap.TransferPolicy.LEAST_TIME,
    })
    transfer.search(
      new AMap.LngLat(origin[0], origin[1]),
      new AMap.LngLat(destination[0], destination[1]),
      (status: string, result: unknown) => {
        try { transfer.destroy?.() } catch { /* best-effort */ }

        if (status !== 'complete') return resolve(null)

        const r = result as {
          plans?: Array<{ distance: number; duration: number; segments?: Array<{ bus?: AMap.BusLine[]; walking?: { steps?: Array<{ path: AMap.LngLat[] }> } }> }>
        }
        const plan = r.plans?.[0]
        if (!plan) return resolve(null)

        // Build polyline by concatenating all segment paths
        const paths: Array<{ lng: number; lat: number }>[] = []
        for (const seg of plan.segments ?? []) {
          if (seg.bus) {
            for (const bus of seg.bus) {
              // Amap BusLine.path returns coordinates along the bus route
              const bp = (bus as any).path as AMap.LngLat[] | undefined
              if (bp) paths.push(bp)
            }
          }
          if (seg.walking?.steps) {
            for (const step of seg.walking.steps) {
              if (step.path) paths.push(step.path)
            }
          }
        }

        const allCoords: string[] = []
        for (const path of paths) {
          for (const pt of path) {
            allCoords.push(`${pt.lng},${pt.lat}`)
          }
        }
        const polyline = allCoords.join(';')

        const distance = plan.distance / 1000
        const duration = plan.duration / 60   // seconds → minutes

        resolve({ polyline, distance: Math.round(distance * 100) / 100, duration: Math.round(duration), mode: 'transit' })
      },
    )
  })
}

/** Build a polyline string from a route's step paths. */
function _encodePolyline(route: { steps?: Array<{ path: AMap.LngLat[] }> }): string {
  const coords: string[] = []
  for (const step of route.steps ?? []) {
    for (const pt of step.path ?? []) {
      coords.push(`${pt.lng},${pt.lat}`)
    }
  }
  return coords.join(';')
}
