import { test, expect } from '@playwright/test'

test.describe('Home Page', () => {
  test('should load the home page', async ({ page }) => {
    await page.goto('/')
    await expect(page).toHaveTitle('frontend')
  })

  test('should display map and chat panel side by side', async ({ page }) => {
    await page.goto('/')

    const homeView = page.locator('.home-view')
    await expect(homeView).toBeVisible()

    const mapArea = page.locator('.home-view__map')
    await expect(mapArea).toBeVisible()

    const chatArea = page.locator('.home-view__chat')
    await expect(chatArea).toBeVisible()
  })

  test('should show chat panel with header and empty state', async ({ page }) => {
    await page.goto('/')

    const chatPanel = page.locator('.chat-panel')
    await expect(chatPanel).toBeVisible()

    const title = page.locator('.chat-panel__title')
    await expect(title).toHaveText('AI 旅行助手')

    const subtitle = page.locator('.chat-panel__subtitle')
    await expect(subtitle).toHaveText('智能行程规划')

    const emptyState = page.locator('.chat-panel__empty')
    await expect(emptyState).toBeVisible()

    const emptyIcon = page.locator('.empty-icon')
    await expect(emptyIcon).toBeVisible()

    const emptyTitle = page.locator('.empty-title')
    await expect(emptyTitle).toHaveText('开始对话')
  })

  test('should navigate to 404 for unknown routes', async ({ page }) => {
    await page.goto('/nonexistent-route')

    const notFoundView = page.locator('.not-found-view')
    await expect(notFoundView).toBeVisible()
  })
})
