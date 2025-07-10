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

test('all-day timeline clears on date change', async ({ page }) => {
  await pseudoLogin(page);

  let call = 0;
  await page.route('**/api/calendar**', route => {
    call++;
    const events = call === 1
      ? [{
          id: 'evA',
          start_utc: '2025-01-01T00:00:00Z',
          end_utc: '2025-01-02T00:00:00Z',
          title: 'All Day A',
          all_day: true,
        }]
      : [];
    route.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify(events) });
  });

  await page.goto('/');

  const timeline = page.locator('#all-day-timeline > li');
  await expect(timeline).toHaveCount(1);

  await page.evaluate(() => {
    const input = document.getElementById('input-date') as HTMLInputElement;
    input.value = '2025-01-02';
    input.dispatchEvent(new Event('change', { bubbles: true }));
  });

  await expect(timeline).toHaveCount(0);
});

test('all-day timeline clears after generating schedule', async ({ page }) => {
  await pseudoLogin(page);

  let call = 0;
  await page.route('**/api/calendar**', route => {
    call++;
    const events = call === 1
      ? [{
          id: 'evB',
          start_utc: '2025-01-01T00:00:00Z',
          end_utc: '2025-01-02T00:00:00Z',
          title: 'All Day B',
          all_day: true,
        }]
      : [];
    route.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify(events) });
  });

  await page.route('**/api/schedule/generate**', route => {
    const body = JSON.stringify({ date: '2025-01-01', slots: new Array(144).fill(0), unplaced: [] });
    route.fulfill({ status: 200, contentType: 'application/json', body });
  });

  await page.goto('/');

  const timeline = page.locator('#all-day-timeline > li');
  await expect(timeline).toHaveCount(1);

  await page.getByTestId('generate-btn').click();

  await expect(timeline).toHaveCount(0);
});

test('all-day event updates when selecting a new date', async ({ page }) => {
  await pseudoLogin(page);

  let call = 0;
  await page.route('**/api/calendar**', route => {
    call++;
    const events = call === 1
      ? [{
          id: 'evD1',
          start_utc: '2025-01-01T00:00:00Z',
          end_utc: '2025-01-02T00:00:00Z',
          title: 'All Day 1',
          all_day: true,
        }]
      : [{
          id: 'evD2',
          start_utc: '2025-01-02T00:00:00Z',
          end_utc: '2025-01-03T00:00:00Z',
          title: 'All Day 2',
          all_day: true,
        }];
    route.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify(events) });
  });

  await page.goto('/');

  const timeline = page.locator('#all-day-timeline > li');
  await expect(timeline).toHaveCount(1);
  await expect(timeline.first()).toContainText('All Day 1');

  await page.evaluate(() => {
    const input = document.getElementById('input-date') as HTMLInputElement;
    input.value = '2025-01-02';
    input.dispatchEvent(new Event('change', { bubbles: true }));
  });

  await expect(timeline).toHaveCount(1);
  await expect(timeline.first()).toContainText('All Day 2');
  await expect(page.locator('#all-day-timeline').getByText('All Day 1')).toHaveCount(0);
});
