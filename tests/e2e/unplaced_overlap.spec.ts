import { test, expect } from '@playwright/test';

// Scenario: overlapping long tasks that can't all be scheduled

test('overlap tasks trigger toast and red card', async ({ page, request }) => {
  /* ---- 1. Create two long tasks starting at noon ---- */
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

  /* ---- 2. Generate schedule ---- */
  await page.goto('/');
  await page.getByTestId('generate-btn').click();

  /* ---- 3. Verify toast appears ---- */
  const toastText = page.locator('text=/未配置: Overlap[12]/');
  await expect(toastText).toBeVisible({ timeout: 5000 });

  const toast = page.locator('.schedule-toast');
  await expect(toast).toHaveCount(1);
  await expect(toast).toHaveAttribute('role', 'status');
  await expect(toast).toHaveAttribute('aria-live', 'polite');

  /* ---- 4. Unplaced card highlighted ---- */
  const card = page.locator('[data-task-id]').filter({ hasText: 'Overlap2' });
  await expect(card).toHaveClass(/bg-red-300/);
});
