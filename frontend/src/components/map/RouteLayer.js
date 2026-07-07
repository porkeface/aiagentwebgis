/**
 * RouteLayerRenderer — draws daily route polylines on an Amap v2 map.
 *
 * For each visible day:
 *   - If the plan carries per-segment data (segments[]), each segment is
 *     drawn independently so a walking leg can render as a same-colour dashed
 *     line while driving / transit legs stay solid.
 *   - Otherwise we fall back to the day-level `polyline` as a single solid
 *     line — same behaviour as before this change.
 *
 * Numbered stop markers continue to be drawn per POI, untouched.
 */

// @ts-nocheck — AMap is loaded dynamically, types are not available at compile time

import { DAY_COLORS } from '@/utils/constants'

// ── Constants ──────────────────────────────────────────────────────────────
const ACTIVE_OPACITY = 0.92
const LINE_WEIGHT_ACTIVE = 5

/** Modes that should render as a dashed line on the map. */
const DASHED_MODES = new Set(['walking'])

// ── Polyline decoder ───────────────────────────────────────────────────────
function decodeAmapPolyline(polyline) {
  if (!polyline) return []
  return polyline
    .split(';')
    .map((pair) => {
      const [lng, lat] = pair.split(',').map(Number)
      // Amap expects [lng, lat] — keep as-is
      return [lng, lat]
    })
    .filter(([lng, lat]) => !isNaN(lng) && !isNaN(lat))
}

// ── Helpers ────────────────────────────────────────────────────────────────
function getDayColor(day) {
  return DAY_COLORS[(day - 1) % DAY_COLORS.length]
}

function buildStopContent(color, num, position) {
  const size = position === 'start' || position === 'end' ? 28 : 24
  return `<div style="
    width:${size}px;height:${size}px;
    background:${color};
    border-radius:50%;display:flex;align-items:center;justify-content:center;
    color:#fff;font-size:11px;font-weight:700;
    border:2px solid #fff;box-shadow:0 1px 4px rgba(0,0,0,0.3);
  ">${num}</div>`
}

/** Two-point straight line between adjacent POIs, used when a segment
 *  has no polyline of its own *and* the whole-day polyline is also empty. */
function fallbackCoordsForSegment(pois, index) {
  const from = pois[index]
  const to = pois[index + 1]
  if (!from || !to) return []
  if (typeof from.lng !== 'number' || typeof from.lat !== 'number') return []
  if (typeof to.lng !== 'number' || typeof to.lat !== 'number') return []
  return [
    [from.lng, from.lat],
    [to.lng, to.lat],
  ]
}

/** Slice a per-day polyline into the i-th sub-segment (POI[i] → POI[i+1]).
 *
 *  The backend's `submit_plan.route_one_day` only returns one full-day
 *  polyline; per-segment polylines are usually empty. We split the day
 *  polyline at the position of POI[i+1] so each segment still shows the
 *  real road path rather than collapsing to a straight POI→POI line.
 *
 *  Matching strategy: walk the day coords, find the index of the coord
 *  closest to POI[i+1] and the index of the coord closest to POI[i] (i.e.
 *  the start of the *next* sub-segment, or the day end), then return the
 *  slice between them. */
function sliceDayPolylineForSegment(dayCoords, pois, index) {
  if (dayCoords.length < 2 || pois.length < 2) return []

  const from = pois[index]
  const to = pois[index + 1]
  if (!from || !to) return []
  if (typeof from.lng !== 'number' || typeof to.lng !== 'number') return []

  // The full-day polyline visits each POI *in order*. The first coord
  // matches POI[0]; the last matches POI[pois.length-1]. We pick the index
  // of the coord closest to POI[index] (the segment start) and closest
  // to POI[index+1] (the segment end).
  const startIdx = nearestCoordIndex(dayCoords, from.lng, from.lat)
  const endIdx = nearestCoordIndex(dayCoords, to.lng, to.lat)

  if (startIdx === -1 || endIdx === -1 || endIdx <= startIdx) {
    return []
  }

  // Include one trailing coord at POI[index+1] so the drawn line ends
  // exactly on the stop marker.
  return dayCoords.slice(startIdx, endIdx + 1)
}

function nearestCoordIndex(coords, lng, lat) {
  let best = -1
  let bestDist = Infinity
  for (let i = 0; i < coords.length; i++) {
    const c = coords[i]
    const dx = c[0] - lng
    const dy = c[1] - lat
    const d = dx * dx + dy * dy
    if (d < bestDist) {
      bestDist = d
      best = i
    }
  }
  return best
}

// ── Class ──────────────────────────────────────────────────────────────────

export class RouteLayerRenderer {
  constructor(AMap) {
    this._AMap = AMap
    /** @type {AMap.Map | null} */
    this._map = null
    /** @type {import('@/stores/map').DailyPlan[]} */
    this._plans = []
    /** @type {number} */
    this._activeDay = 0
    /** @type {AMap.Polyline[]} */
    this._lines = []
    /** @type {AMap.Marker[]} */
    this._markers = []
    /** @type {AMap.Marker[]} */
    this._poiMarkers = []
    /** @type {(poi: import('@/types').POI) => void} */
    this._onPoiClick = null
  }

  // ── Public API ─────────────────────────────────────────────────────────

  /**
   * Set the callback for POI marker clicks.
   * @param {(poi: import('@/types').POI) => void} fn
   */
  onPoiClick(fn) {
    this._onPoiClick = fn
  }

  /**
   * Show search-result POIs on the map immediately (before route planning).
   * @param {import('@/types').POI[]} pois
   * @param {Set<string>} [routePoiIds] — IDs of POIs that are already shown as route stops
   */
  setPois(pois, routePoiIds) {
    this._clearPoiMarkers()
    if (!this._map || !this._AMap) return
    const clickFn = this._onPoiClick
    const skipIds = routePoiIds || new Set()
    for (const poi of pois) {
      // Skip POIs that are already displayed as route stop markers
      if (skipIds.has(String(poi.id))) continue
      const content = `<div class="poi-dot" data-poi-id="${poi.id}" style="
        width:22px;height:22px;
        background:#e8623c;border-radius:50%;
        border:2px solid #fff;box-shadow:0 1px 3px rgba(0,0,0,0.3);
        cursor:pointer;
      "></div>`
      const marker = new this._AMap.Marker({
        position: [poi.lng, poi.lat],
        content,
        offset: new this._AMap.Pixel(-12, -12),
        zIndex: 200,
      })
      if (clickFn) {
        marker.on('click', () => clickFn(poi))
      }
      this._map.add(marker)
      this._poiMarkers.push(marker)
    }
  }

  /**
   * Replace all routes and re-render.
   * @param {import('@/stores/map').DailyPlan[]} plans
   * @param {number} activeDay — 0 = all days
   */
  setRoutes(plans, activeDay) {
    this._plans = plans
    this._activeDay = activeDay
    this._render()
  }

  /**
   * Switch the active day filter.
   * @param {number} day — 0 = all days
   */
  setActiveDay(day) {
    if (this._activeDay === day) return
    this._activeDay = day
    this._render()
  }

  /** Attach to a new map instance (auto-detected on first render). */
  attach(map) {
    this._map = map
  }

  /** Remove all overlays from the map. */
  destroy() {
    this._clear()
    this._clearPoiMarkers()
    this._map = null
  }

  // ── Internal ───────────────────────────────────────────────────────────

  _clear() {
    const map = this._map
    if (!map) return
    for (const l of this._lines) map.remove(l)
    for (const m of this._markers) map.remove(m)
    this._lines = []
    this._markers = []
  }

  _clearPoiMarkers() {
    const map = this._map
    if (!map) return
    for (const m of this._poiMarkers) map.remove(m)
    this._poiMarkers = []
  }

  _render() {
    if (!this._AMap) return
    if (!this._map) {
      const maps = document.querySelectorAll('.amap-container')
      this._map = this._findMapInstance()
    }
    if (!this._map) return

    this._clear()
    // Keep standalone POI markers visible when routes are rendered
    // _clearPoiMarkers() is NOT called here — only in setPois() which
    // replaces the full set atomically.

    const visibleDays = this._activeDay === 0
      ? new Set(this._plans.map((p) => p.day))
      : new Set([this._activeDay])

    const clickFn = this._onPoiClick

    for (const plan of this._plans) {
      if (!visibleDays.has(plan.day)) continue

      const color = getDayColor(plan.day)
      const pois = plan.pois ?? []

      // ── Polylines — per-segment with fallback to whole-day polyline ───
      const segments = plan.segments ?? []
      const drawWholeDayFallback = segments.length === 0

      if (drawWholeDayFallback) {
        let coords = decodeAmapPolyline(plan.polyline ?? '')
        if (coords.length < 2 && pois.length >= 2) {
          coords = pois
            .filter((p) => typeof p.lng === 'number' && typeof p.lat === 'number')
            .map((p) => [p.lng, p.lat])
        }
        if (coords.length >= 2) {
          this._drawSegment(coords, color, 'driving', false)
        }
      } else {
        // Pre-decode the full-day polyline once so we can slice per
        // segment when the backend didn't ship a per-segment polyline.
        const dayCoords = decodeAmapPolyline(plan.polyline ?? '')

        for (let i = 0; i < segments.length; i++) {
          const seg = segments[i]
          const mode = seg?.mode ?? 'driving'

          // 1) Per-segment polyline (richest source — kept for future
          //    backends that ship it).
          let segCoords = decodeAmapPolyline(seg?.polyline ?? '')

          // 2) Slice the full-day polyline between POI[i] and POI[i+1].
          //    This is the common case today: the backend's
          //    `submit_plan.route_one_day` only stores one full-day
          //    polyline, so each segment must be carved out of it.
          if (segCoords.length < 2 && dayCoords.length >= 2) {
            segCoords = sliceDayPolylineForSegment(dayCoords, pois, i)
          }

          // 3) Last resort: straight line between the two POIs.
          if (segCoords.length < 2) {
            segCoords = fallbackCoordsForSegment(pois, i)
          }

          if (segCoords.length >= 2) {
            this._drawSegment(segCoords, color, mode, false)
          }
        }
      }

      // ── Stop markers ─────────────────────────────────────────────────────
      const count = pois.length
      for (let i = 0; i < count; i++) {
        const poi = pois[i]
        let position = 'mid'
        if (count === 1) position = 'start'
        else if (i === 0) position = 'start'
        else if (i === count - 1) position = 'end'

        const zIndex = position === 'start' ? 500 : (position === 'end' ? 400 : 300)
        const content = buildStopContent(color, i + 1, position)

        const marker = new this._AMap.Marker({
          position: [poi.lng, poi.lat],
          content,
          offset: new this._AMap.Pixel(-14, -14),
          zIndex,
        })
        if (clickFn) {
          marker.on('click', () => clickFn(poi))
        }
        this._map.add(marker)
        this._markers.push(marker)
      }
    }
  }

  /**
   * Draw one polyline with a white outline + coloured stroke. Walking
   * segments render as `dashed` (with `strokeDasharray` as a fallback for
   * older Amap versions); every other mode renders solid.
   *
   * @param {[number, number][]} coords  Amap [lng, lat] pairs
   * @param {string} color               Hex stroke colour
   * @param {string} mode                'walking' | 'driving' | 'transit'
   * @param {boolean} _isOutline         Kept for future use; outline layer
   *                                     is always drawn white beneath.
   */
  _drawSegment(coords, color, mode, _isOutline) {
    const dashed = DASHED_MODES.has(mode)
    const dashConfig = dashed
      ? { strokeStyle: 'dashed', strokeDasharray: [8, 6] }
      : { strokeStyle: 'solid' }

    // White outline (underneath)
    const outline = new this._AMap.Polyline({
      path: coords,
      strokeColor: '#ffffff',
      strokeWeight: LINE_WEIGHT_ACTIVE + 4,
      strokeOpacity: 0.9,
      lineJoin: 'round',
      lineCap: 'round',
      isOutline: false,
      showDir: false,
      zIndex: 10,
      // Outlines never need dashing — keeps the white halo continuous.
      strokeStyle: 'solid',
      strokeDasharray: undefined,
    })
    this._map.add(outline)
    this._lines.push(outline)

    // Coloured route line with DIRECTION ARROWS — the key feature
    const routeLine = new this._AMap.Polyline({
      path: coords,
      strokeColor: color,
      strokeWeight: LINE_WEIGHT_ACTIVE,
      strokeOpacity: ACTIVE_OPACITY,
      lineJoin: 'round',
      lineCap: 'round',
      showDir: true,
      dirColor: color,
      dirImg: undefined,  // use Amap's built-in arrow
      zIndex: 11,
      ...dashConfig,
    })
    this._map.add(routeLine)
    this._lines.push(routeLine)
  }

  /**
   * Try to find the Amap Map instance from the DOM.
   * Amap stores the map instance on the container element.
   */
  _findMapInstance() {
    // The Amap SDK stores the map instance globally — find it by iterating
    // over known container element
    const container = document.getElementById('amap-container')
    if (container && container._amap) {
      return container._amap
    }
    // Alternative: check global AMap instances
    // Amap v2 stores instances internally; we expose it from MapView
    return null
  }
}