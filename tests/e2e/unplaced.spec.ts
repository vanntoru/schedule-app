import { test, expect } from '@playwright/test';

const BASE = 'http://localhost:5173';   // テスト用サーバ

test('unplaced task shows red highlight & toast', async ({ page, request }) => {
  /* ------- 1. 24 h を越えるタスクを 2 件投入して容量オーバーにする ------- */
  for (const i of [1, 2]) {
    await request.post(`${BASE}/api/tasks`, {
      data: {
        title: `TooLong${i}`,
        category: 'e2e',
        duration_min: 900,          // 15 h × 2 = 30 h > 24 h
        duration_raw_min: 900,
        priority: 'A'
      }
    });
  }

  /* ------- 2. 画面を開き Generate ▶ をクリック ------- */
  await page.goto(BASE);
  await page.getByTestId('generate-btn').click();

  /* ------- 3. Toast が表示される ------- */
  const toastText = page.locator('text=/未配置: TooLong[12]/');   // どちらか 1 件を許容
  await expect(toastText).toBeVisible({ timeout: 5000 });

  // Toast should be unique and have proper ARIA attributes
  const toast = page.locator('.schedule-toast');
  await expect(toast).toHaveCount(1);
  await expect(toast).toHaveAttribute('role', 'status');
  await expect(toast).toHaveAttribute('aria-live', 'polite');

  /* ------- 4. サイドパネルのカードに赤クラスが付く ------- */
  const card = page.locator('[data-task-id]').filter({ hasText: 'TooLong2' });
  await expect(card).toHaveClass(/bg-red-300/);
});
