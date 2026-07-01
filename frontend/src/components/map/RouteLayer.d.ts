import type { DailyPlan } from '@/stores/map'

export class RouteLayerRenderer {
  constructor(AMap: typeof AMap)
  setRoutes(plans: DailyPlan[], activeDay: number): void
  setActiveDay(day: number): void
  attach(map: AMap.Map): void
  destroy(): void
}
