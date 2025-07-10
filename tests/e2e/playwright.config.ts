import { defineConfig } from '@playwright/test';

export default defineConfig({
  testDir: './tests/e2e',
  timeout: 30000,
  expect: {
    timeout: 5000,
  },
  use: {
    trace: 'retain-on-failure',
    headless: true,
    baseURL: 'http://localhost:5173',
  },
  webServer: {
    command: 'flask --app schedule_app run --port 5173',
    url: 'http://localhost:5173',
    timeout: 120 * 1000,
    env: { GCP_PROJECT: 'dummy-project', GOOGLE_CLIENT_ID: 'dummy-client-id' },
    reuseExistingServer: !process.env.CI,
  },
});
