import { test, expect } from '@playwright/test';
import { pseudoLogin, mockGoogleCalendar } from './helpers';

test('top page loads with correct title', async ({ page }) => {
  await page.goto('/');
  await expect(page).toHaveTitle('1-Day Schedule');
});

test('page shows logged-in state after pseudo login and reload', async ({ page }) => {
  await mockGoogleCalendar(page, [
    {
      id: 'ev0',
      start_utc: '2025-01-01T09:00:00Z',
      end_utc: '2025-01-01T10:00:00Z',
      title: 'Timed Event',
      all_day: false,
    },
    {
      id: 'ev1',
      start_utc: '2025-01-01T00:00:00Z',
      end_utc: '2025-01-02T00:00:00Z',
      title: 'All Day',
      all_day: true,
    },
  ]);

  await pseudoLogin(page);
  await page.goto('/');

  // Only the all-day event should appear on the timeline
  const timeline = page.locator('#all-day-timeline > li');
  await expect(timeline).toHaveCount(1);

  // Reload and verify the logged-in UI persists
  await page.reload();
  await expect(timeline).toHaveCount(1);
});
