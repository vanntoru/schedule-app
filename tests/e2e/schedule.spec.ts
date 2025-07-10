import { test, expect } from '@playwright/test';
import { pseudoLogin, mockGoogleCalendar } from './helpers';

test('top page loads with correct title', async ({ page }) => {
  await page.goto('/');
  await expect(page).toHaveTitle('1-Day Schedule');
});

test('page shows logged-in state after pseudo login and reload', async ({ page }) => {
  await mockGoogleCalendar(page, [
    {
      id: 'ev1',
      start_utc: '2025-01-01T09:00:00Z',
      end_utc: '2025-01-01T10:00:00Z',
      title: 'Sample Event',
      all_day: false,
    },
  ]);

  await pseudoLogin(page);
  await page.goto('/');

  // All-day timeline should contain the mocked event
  const timeline = page.locator('#all-day-timeline > li');
  await expect(timeline).toHaveCount(1);

  // Reload and verify the logged-in UI persists
  await page.reload();
  await expect(timeline).toHaveCount(1);
});
