import { test, expect } from '@playwright/test';

// Ensure the service worker registers and becomes active

test('service worker registration', async ({ page }) => {
  await page.goto('/');

  await page.waitForFunction(() => navigator.serviceWorker.controller !== null);

  const hasController = await page.evaluate(() => !!navigator.serviceWorker.controller);
  expect(hasController).toBe(true);
});
