import { defineConfig, devices } from '@playwright/test';

export default defineConfig({
  testDir: './tests/e2e',
  timeout: 30000,
  expect: {
    timeout: 5000,
  },
  fullyParallel: true,
  retries: 2,
  reporter: [['html', { open: 'never' }]],
  use: {
    trace: 'on',
    baseURL: 'http://localhost:5173',
  },
  webServer: {
    command: 'python -m flask --app schedule_app run --port 5173',
    url: 'http://localhost:5173',
    reuseExistingServer: !process.env.CI,
  },
  projects: [
    {
      name: 'chromium',
      use: { ...devices['Desktop Chrome'] },
    },
  ],
});
