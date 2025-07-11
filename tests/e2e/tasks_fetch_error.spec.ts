import { test, expect } from '@playwright/test';
import { mockGoogleCalendar } from './helpers';

test('tasks API error shows toast', async ({ page }) => {
  // Prevent calendar fetch from redirecting
  await mockGoogleCalendar(page);

  // Fail the tasks API request
  await page.route('**/api/tasks', route =>
    route.fulfill({
      status: 502,
      contentType: 'application/json',
      body: JSON.stringify({ detail: 'server error' })
    })
  );

  await page.goto('/');

  const toast = page.locator('.schedule-toast');
  await expect(toast).toHaveCount(1);
  await expect(toast).toBeVisible();
  await expect(toast).toContainText('server error');
});
