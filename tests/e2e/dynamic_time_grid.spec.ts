import { test, expect } from '@playwright/test';

test('app.js injects time grid when missing', async ({ page }) => {
  // Mock API endpoints to prevent network errors
  await page.route('**/api/**', route => {
    route.fulfill({ status: 200, body: '[]', contentType: 'application/json' });
  });

  await page.goto('/static/test/minimal.html');

  const grid = page.locator('#time-grid');
  await expect(grid).toBeVisible();
  await expect(grid.locator('.slot')).toHaveCount(144);
});
