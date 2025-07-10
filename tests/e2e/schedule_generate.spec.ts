import { test, expect } from '@playwright/test';

// Verify clicking Generate ▶ calls the schedule API and renders returned grid

test('schedule generation renders grid', async ({ page }) => {
  // Mock calendar API to avoid 401 redirect
  await page.route('**/api/calendar**', route =>
    route.fulfill({ status: 200, contentType: 'application/json', body: '[]' })
  );

  // Prepare predictable schedule response
  const grid = new Array(144).fill(0);
  grid[0] = 1; // busy slot
  grid[1] = 2; // task slot

  await page.route('**/api/schedule/generate**', route =>
    route.fulfill({
      status: 200,
      contentType: 'application/json',
      body: JSON.stringify({ date: '2025-01-01', slots: grid, unplaced: [] })
    })
  );

  await page.goto('/');

  const [req] = await Promise.all([
    page.waitForRequest(r => r.url().includes('/api/schedule/generate')),
    page.getByTestId('generate-btn').click()
  ]);

  expect(req.method()).toBe('POST');

  const slot0 = page.locator('[data-slot-index="0"]');
  const slot1 = page.locator('[data-slot-index="1"]');

  await expect(slot0).toHaveClass(/bg-gray-200/);
  await expect(slot0).toHaveClass(/grid-slot--busy/);
  await expect(slot1).toHaveClass(/bg-green-200/);
  await expect(slot1).toHaveClass(/grid-slot--busy/);
});
