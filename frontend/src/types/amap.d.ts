/**
 * Minimal type declarations for AMap JS API v2 — sufficient for our usage.
 *
 * These are intentionally narrow.  Expand as we use more of the AMap API surface.
 * @see https://lbs.amap.com/api/javascript-api-v2/documentation
 */

declare namespace AMap {
  // ── Map ─────────────────────────────────────────────────────────────────
  interface MapOptions {
    center?: [number, number] | LngLat
    zoom?: number
    viewMode?: '2D' | '3D'
    resizeEnable?: boolean
    showBuildingBlock?: boolean
    dragEnable?: boolean
    zoomEnable?: boolean
    doubleClickZoom?: boolean
    scrollWheel?: boolean
    animateEnable?: boolean
    [key: string]: unknown
  }

  class Map {
    constructor(container: string | HTMLDivElement, opts?: MapOptions)
    setZoomAndCenter(zoom: number, center: [number, number]): void
    setBounds(bounds: Bounds, immediately?: boolean, padding?: number[]): void
    add(overlay: unknown): void
    remove(overlay: unknown): void
    destroy(): void
  }

  // ── Bounds ──────────────────────────────────────────────────────────────
  class Bounds {
    constructor(min: [number, number], max: [number, number])
  }

  // ── Coordinates ─────────────────────────────────────────────────────────
  class LngLat {
    constructor(lng: number, lat: number)
    lng: number
    lat: number
  }

  class Pixel {
    constructor(x: number, y: number)
  }

  // ── Polyline ────────────────────────────────────────────────────────────
  interface PolylineOptions {
    path: [number, number][] | LngLat[]
    strokeColor?: string
    strokeWeight?: number
    strokeOpacity?: number
    lineJoin?: 'round' | 'miter' | 'bevel'
    lineCap?: 'round' | 'butt' | 'square'
    isOutline?: boolean
    showDir?: boolean
    dirColor?: string
    dirImg?: string
    zIndex?: number
  }

  class Polyline {
    constructor(opts?: PolylineOptions)
  }

  // ── Marker ──────────────────────────────────────────────────────────────
  interface MarkerOptions {
    position: [number, number] | LngLat
    content?: string
    offset?: Pixel
    zIndex?: number
  }

  class Marker {
    constructor(opts?: MarkerOptions)
    on(event: string, handler: () => void): void
  }

  // ── Text ────────────────────────────────────────────────────────────────
  interface TextStyle {
    'font-size'?: string
    'background'?: string
    'padding'?: string
    'border-radius'?: string
    'white-space'?: string
    'color'?: string
    'opacity'?: number
  }

  interface TextOptions {
    text: string
    position: [number, number] | LngLat
    style?: TextStyle
    zIndex?: number
  }

  class Text {
    constructor(opts?: TextOptions)
  }
}
