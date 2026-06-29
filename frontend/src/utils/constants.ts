import { divIcon, type Icon, type IconOptions, type DivIconOptions } from 'leaflet'

/**
 * Day-route color palette.
 * Mirrors CSS variables --color-day-1 .. --color-day-4 in style.css.
 * Use this array when colors are needed in JS (e.g. inline styles for divIcons).
 */
export const DAY_COLORS = ['#1890ff', '#52c41a', '#fa8c16', '#a855f7'] as const

/**
 * Create a leaflet DivIcon that satisfies vue-leaflet's LMarker `:icon` prop.
 *
 * vue-leaflet types the prop as `Icon<IconOptions>` which requires `iconUrl: string`,
 * but `divIcon()` returns `DivIcon` (extending `Icon<DivIconOptions>`) where `iconUrl`
 * is optional. The runtime works fine — this helper bridges the type gap with a cast.
 */
export function createDivIcon(options: DivIconOptions): Icon<IconOptions> {
  return divIcon(options) as unknown as Icon<IconOptions>
}
