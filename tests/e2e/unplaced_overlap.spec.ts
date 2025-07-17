import { test, expect } from '@playwright/test';
import { mockGoogleCalendar } from './helpers';

// Scenario: overlapping long tasks that can't all be scheduled

test('overlap tasks trigger toast and red card', async ({ page, request }) => {
  /* ---- 1. Clear existing tasks and create two long ones ---- */
  const existing = await request.get('/api/tasks');
  for (const t of await existing.json()) {
    await request.delete(`/api/tasks/${t.id}`);
  }

  for (const i of [1, 2]) {
    await request.post('/api/tasks', {
      data: {
        title: `Overlap${i}`,
        category: 'e2e',
        duration_min: 600,        // 10 hours
        duration_raw_min: 600,
        priority: 'A',
        earliest_start_utc: '2025-01-01T12:00:00Z',
      }
    });
  }

  /* ---- 2. Generate schedule on 2025-01-01 ---- */
  await mockGoogleCalendar(page);
  await page.goto('/');
  await page.evaluate(() => {
    const input = document.getElementById('input-date') as HTMLInputElement;
    input.value = '2025-01-01';
    input.dispatchEvent(new Event('change', { bubbles: true }));
  });
  await page.getByTestId('generate-btn').click();

  /* ---- 3. Verify toast appears ---- */
  const toastText = page.locator('text=/未配置: Overlap[12]/');
  await toastText.waitFor({ state: 'visible' });
  await expect(toastText).toBeVisible({ timeout: 5000 });

  const toast = page.locator('.schedule-toast');
  await expect(toast).toHaveCount(1);
  await expect(toast).toHaveAttribute('role', 'status');
  await expect(toast).toHaveAttribute('aria-live', 'polite');

  /* ---- 4. Unplaced card highlighted ---- */
  const card = page.locator('[data-task-id]').filter({ hasText: 'Overlap2' });
  await expect(card).toHaveClass(/bg-red-300/);
});
