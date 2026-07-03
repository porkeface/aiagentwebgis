import { test, expect, type Page } from '@playwright/test'

/**
 * E2E coverage for the per-segment mode switcher introduced in
 * DayCard.vue + the dashed polyline rendering in RouteLayer.js.
 *
 * The spec depends on a seeded trip with id 1 that has at least one day
 * containing >= 2 POIs. Skip with `SKIP_TRIP_E2E=1` if the fixture is
 * not present in the dev backend.
 */

const TRIP_ID = 1
const TRIP_URL = `/trips/${TRIP_ID}`

const skipIfNoFixture = process.env.SKIP_TRIP_E2E === '1'

test.describe('TripDetail — per-segment mode switcher', () => {
  test.skip(skipIfNoFixture, 'Seeded trip fixture not available; set SKIP_TRIP_E2E=0 to enable.')

  test.beforeEach(async ({ page }) => {
    await page.goto(TRIP_URL)
    // Wait for the day card to render so we know segments are loaded.
    await expect(page.locator('.day-card').first()).toBeVisible({ timeout: 15_000 })
  })

  test('each segment renders a mode chip with an icon', async ({ page }) => {
    const chips = page.locator('.poi-segment .mode-chip')
    const count = await chips.count()
    expect(count).toBeGreaterThan(0)

    // The first chip should be one of the three supported modes.
    const firstClass = await chips.first().getAttribute('class')
    expect(firstClass).toMatch(/mode-chip--(walking|driving|transit)/)
  })

  test('clicking a chip opens a popover with three mode options', async ({ page }) => {
    const chip = page.locator('.poi-segment .mode-chip').first()
    await chip.click()

    const options = page.locator('.mode-pop__opt')
    await expect(options).toHaveCount(3)
    await expect(options.nth(0)).toContainText('步行')
    await expect(options.nth(1)).toContainText('驾车')
    await expect(options.nth(2)).toContainText('公交')
  })

  test('selecting transit updates the visible duration', async ({ page }) => {
    const segment = page.locator('.poi-segment').first()
    const durBefore = (await segment.locator('.segment-dur').textContent())?.trim() ?? ''

    await segment.locator('.mode-chip').click()
    await page.locator('.mode-pop__opt:has-text("公交")').click()

    // Allow Vue's reactive update to flush.
    await page.waitForTimeout(150)

    const durAfter = (await segment.locator('.segment-dur').textContent())?.trim() ?? ''
    expect(durAfter).not.toBe(durBefore)
    // Sanity: 公交 estimates ≥ 步行 estimates at any distance.
    expect(durAfter).not.toBe('—')
  })

  test('selecting walking updates the chip label and colour', async ({ page }) => {
    const segment = page.locator('.poi-segment').first()
    await segment.locator('.mode-chip').click()
    await page.locator('.mode-pop__opt:has-text("步行")').click()
    await page.waitForTimeout(150)

    const chip = segment.locator('.mode-chip')
    await expect(chip).toContainText('步行')
    await expect(chip).toHaveClass(/mode-chip--walking/)
  })

  test('selecting driving updates the chip label and colour', async ({ page }) => {
    const segment = page.locator('.poi-segment').first()
    await segment.locator('.mode-chip').click()
    await page.locator('.mode-pop__opt:has-text("驾车")').click()
    await page.waitForTimeout(150)

    const chip = segment.locator('.mode-chip')
    await expect(chip).toContainText('驾车')
    await expect(chip).toHaveClass(/mode-chip--driving/)
  })

  test('day total uses H+M format and never shows the floating-point bug', async ({ page }) => {
    const stats = page.locator('.day-stats').first()
    const text = (await stats.textContent())?.trim() ?? ''

    // The old bug surfaced as "2h 51.91999999999996m" — assert the dot pattern
    // is never followed by more than one digit inside the H+M portion.
    expect(text).not.toMatch(/\d+h\s+\d+m?\.\d{2,}/)

    // And the day stats should at minimum contain either "min" or an "h" unit.
    expect(text).toMatch(/(min|h)/)
  })
})

/** Convenience helper for ad-hoc local debugging — not a test. */
export async function _debugSnapshot(page: Page): Promise<void> {
  await page.goto(TRIP_URL)
  await expect(page.locator('.day-card').first()).toBeVisible({ timeout: 15_000 })
  await page.screenshot({ path: 'e2e/__screens__/trip-detail.png', fullPage: true })
}
