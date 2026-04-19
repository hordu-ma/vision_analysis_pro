import path from 'node:path'
import { fileURLToPath } from 'node:url'
import { defineConfig, devices } from '@playwright/test'

const webRoot = path.dirname(fileURLToPath(import.meta.url))
const repoRoot = path.resolve(webRoot, '..')

export default defineConfig({
  testDir: './e2e',
  fullyParallel: false,
  timeout: 30_000,
  expect: {
    timeout: 10_000
  },
  workers: process.env.CI ? 1 : undefined,
  reporter: 'list',
  use: {
    baseURL: 'http://127.0.0.1:4173',
    trace: 'on-first-retry',
    screenshot: 'only-on-failure'
  },
  projects: [
    {
      name: 'chromium',
      use: { ...devices['Desktop Chrome'] }
    }
  ],
  webServer: [
    {
      command: 'uv run uvicorn vision_analysis_pro.web.api.main:app --host 127.0.0.1 --port 8000',
      cwd: repoRoot,
      url: 'http://127.0.0.1:8000/api/v1/health',
      reuseExistingServer: !process.env.CI,
      timeout: 120_000,
      env: {
        ...process.env,
        INFERENCE_ENGINE: 'stub',
        API_RELOAD: 'false',
        CORS_ALLOW_ORIGINS: 'http://127.0.0.1:4173'
      }
    },
    {
      command: 'npm run dev -- --host 127.0.0.1 --port 4173',
      cwd: webRoot,
      url: 'http://127.0.0.1:4173',
      reuseExistingServer: !process.env.CI,
      timeout: 120_000,
      env: {
        ...process.env,
        VITE_API_PROXY_TARGET: 'http://127.0.0.1:8000'
      }
    }
  ]
})
