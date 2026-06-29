import { test, expect } from '@playwright/test'

test.describe('Responsive Layout', () => {
  test('should stack vertically on mobile viewport (375px)', async ({
    page,
  }) => {
    await page.setViewportSize({ width: 375, height: 812 })
    await page.goto('/')

    const homeView = page.locator('.home-view')
    await expect(homeView).toBeVisible()

    // On mobile, flex-direction should be column (vertical stack)
    const flexDirection = await homeView.evaluate((el) =>
      window.getComputedStyle(el).flexDirection
    )
    expect(flexDirection).toBe('column')
  })

  test('map should have reduced height on mobile', async ({ page }) => {
    await page.setViewportSize({ width: 375, height: 812 })
    await page.goto('/')

    const mapArea = page.locator('.home-view__map')
    await expect(mapArea).toBeVisible()

    // On mobile the map is 45vh; just check it's visible and has reasonable height
    const box = await mapArea.boundingBox()
    expect(box).not.toBeNull()
    expect(box!.height).toBeGreaterThan(100)
    expect(box!.height).toBeLessThan(600) // should not fill entire screen
  })

  test('chat panel should be visible below map on mobile', async ({
    page,
  }) => {
    await page.setViewportSize({ width: 375, height: 812 })
    await page.goto('/')

    const chatArea = page.locator('.home-view__chat')
    await expect(chatArea).toBeVisible()

    // Chat should be below the map (higher Y position)
    const mapBox = await page.locator('.home-view__map').boundingBox()
    const chatBox = await chatArea.boundingBox()
    expect(mapBox).not.toBeNull()
    expect(chatBox).not.toBeNull()
    expect(chatBox!.y).toBeGreaterThanOrEqual(mapBox!.y + mapBox!.height - 2)
  })

  test('should display side by side on desktop viewport (1280px)', async ({
    page,
  }) => {
    await page.setViewportSize({ width: 1280, height: 800 })
    await page.goto('/')

    const homeView = page.locator('.home-view')
    const flexDirection = await homeView.evaluate((el) =>
      window.getComputedStyle(el).flexDirection
    )
    expect(flexDirection).toBe('row')
  })

  test('chat input should remain usable on small viewport', async ({
    page,
  }) => {
    await page.setViewportSize({ width: 375, height: 812 })
    await page.goto('/')

    const textarea = page.locator('.chat-panel__input textarea')
    await expect(textarea).toBeVisible()

    const sendBtn = page.locator('.chat-panel__send-btn')
    await expect(sendBtn).toBeVisible()

    // Should be able to type
    await textarea.fill('手机测试')
    const value = await textarea.inputValue()
    expect(value).toBe('手机测试')
  })
})
