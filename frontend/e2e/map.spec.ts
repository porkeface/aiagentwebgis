import { test, expect } from '@playwright/test'

test.describe('Map View', () => {
  test('should render the Leaflet map container', async ({ page }) => {
    await page.goto('/')

    const mapContainer = page.locator('.map-container')
    await expect(mapContainer).toBeVisible()
  })

  test('should have a visible Leaflet map element', async ({ page }) => {
    await page.goto('/')

    // vue-leaflet renders .leaflet-container inside .map-container
    const leafletContainer = page.locator('.map-container .leaflet-container')
    await expect(leafletContainer).toBeVisible({ timeout: 10_000 })
  })

  test('should load map tiles', async ({ page }) => {
    await page.goto('/')

    // Leaflet tile pane should exist once the map initializes
    const tilePane = page.locator('.leaflet-tile-pane')
    await expect(tilePane).toBeAttached({ timeout: 10_000 })
  })

  test('map container should have minimum height', async ({ page }) => {
    await page.goto('/')

    const mapContainer = page.locator('.map-container')
    const box = await mapContainer.boundingBox()
    expect(box).not.toBeNull()
    expect(box!.height).toBeGreaterThanOrEqual(300)
    expect(box!.width).toBeGreaterThan(0)
  })
})
