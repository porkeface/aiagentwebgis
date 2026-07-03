import type { DailyPlan } from '@/stores/map'
import type { POI } from '@/types'

export class RouteLayerRenderer {
  constructor(AMap: typeof AMap)
  setRoutes(plans: DailyPlan[], activeDay: number): void
  setActiveDay(day: number): void
  setPois(pois: POI[]): void
  onPoiClick(fn: (poi: POI) => void): void
  attach(map: AMap.Map): void
  destroy(): void
}
