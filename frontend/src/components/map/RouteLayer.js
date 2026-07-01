/**
 * RouteLayerRenderer — draws daily route polylines on an Amap v2 map.
 *
 * Each day gets:
 *   - A white-outline polyline (thicker, semi-transparent)
 *   - A coloured route polyline with ``showDir: true`` for direction arrows
 *   - Numbered stop markers (circle HTML markers)
 *
 * Why pure JS instead of Vue? Amap's overlay API is imperative (``map.add()``)
 * and does not map cleanly to Vue's declarative template model. We minimise
 * the reactive surface to ``setRoutes`` / ``setActiveDay``.
 */

// @ts-nocheck — AMap is loaded dynamically, types are not available at compile time

import { DAY_COLORS } from '@/utils/constants'

// ── Constants ──────────────────────────────────────────────────────────────
const ACTIVE_OPACITY = 0.92
const LINE_WEIGHT_ACTIVE = 5

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
   */
  setPois(pois) {
    this._clearPoiMarkers()
    if (!this._map || !this._AMap) return
    const clickFn = this._onPoiClick
    for (const poi of pois) {
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
    // Auto-detect map from AMap global
    if (!this._map) {
      // Walk Amap instances — there should be one active map
      const maps = document.querySelectorAll('.amap-container')
      // The map instance is stored on the container element by amap
      this._map = this._findMapInstance()
    }
    if (!this._map) return

    this._clear()

    const visibleDays = this._activeDay === 0
      ? new Set(this._plans.map((p) => p.day))
      : new Set([this._activeDay])

    const clickFn = this._onPoiClick

    for (const plan of this._plans) {
      if (!visibleDays.has(plan.day)) continue

      const color = getDayColor(plan.day)
      const pois = plan.pois ?? []

      // ── Polyline ──────────────────────────────────────────────────────────
      let coords = decodeAmapPolyline(plan.polyline ?? '')
      if (coords.length < 2 && pois.length >= 2) {
        coords = pois
          .filter((p) => typeof p.lng === 'number' && typeof p.lat === 'number')
          .map((p) => [p.lng, p.lat])
      }

      if (coords.length >= 2) {
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
        })
        this._map.add(routeLine)
        this._lines.push(routeLine)
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