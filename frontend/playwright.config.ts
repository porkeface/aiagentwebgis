import { defineConfig, devices } from '@playwright/test'

/**
 * Playwright config for aiagentwebgis/frontend.
 *
 * Boots the Vite dev server on port 5173 and tears it down after the run.
 * Only the trip-detail segment-mode spec lives under e2e/ today; extend the
 * testDir + match patterns if more specs land later.
 */
export default defineConfig({
  testDir: './e2e',
  testMatch: /.*\.spec\.ts$/,
  fullyParallel: true,
  forbidOnly: !!process.env.CI,
  retries: process.env.CI ? 2 : 0,
  reporter: process.env.CI ? 'github' : 'list',
  use: {
    baseURL: 'http://localhost:5173',
    trace: 'on-first-retry',
    // Provide a Chinese locale for our zh-CN UI strings.
    locale: 'zh-CN',
  },
  projects: [
    {
      name: 'chromium',
      use: { ...devices['Desktop Chrome'] },
    },
  ],
  webServer: {
    command: 'npm run dev',
    url: 'http://localhost:5173',
    reuseExistingServer: !process.env.CI,
    timeout: 60_000,
  },
})
