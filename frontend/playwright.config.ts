/**
 * Playwright configuration for AI Travel Planner frontend E2E tests.
 *
 * Uses system Chrome (channel: 'chrome') to avoid downloading browser binaries.
 * Tests run against the Vite dev server at localhost:5173.
 *
 * @see https://playwright.dev/docs/test-configuration
 */

// Bypass proxy for localhost (required in environments with system proxy)
process.env.NO_PROXY = process.env.NO_PROXY ?? 'localhost,127.0.0.1'
process.env.no_proxy = process.env.no_proxy ?? 'localhost,127.0.0.1'

import { defineConfig, devices } from '@playwright/test'

export default defineConfig({
  testDir: './e2e',
  fullyParallel: true,
  forbidOnly: !!process.env.CI,
  retries: process.env.CI ? 2 : 0,
  workers: process.env.CI ? 1 : 2,
  reporter: 'html',

  use: {
    baseURL: 'http://localhost:5173',
    trace: 'on-first-retry',
    screenshot: 'only-on-failure',
  },

  projects: [
    {
      name: 'chromium',
      use: {
        ...devices['Desktop Chrome'],
        channel: 'chrome',
        launchOptions: {
          args: [
            '--no-proxy-server',
            '--proxy-bypass-list=localhost;127.0.0.1',
          ],
        },
      },
    },
  ],

  webServer: {
    command: 'npm run dev',
    url: 'http://localhost:5173',
    reuseExistingServer: !process.env.CI,
    timeout: 30_000,
    env: {
      NO_PROXY: 'localhost,127.0.0.1',
      no_proxy: 'localhost,127.0.0.1',
    },
  },
})
