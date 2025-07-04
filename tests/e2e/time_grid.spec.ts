import { test, expect } from '@playwright/test';

test.describe('Time Grid rendering', () => {

  test('should display exactly 144 time slots', async ({ page }) => {
    // Webアプリを起動しているURLにアクセス
    await page.goto('/');

    // Time Grid が存在することを確認
    const timeGrid = page.locator('#time-grid');
    await expect(timeGrid).toBeVisible();

    // .slot要素が144個あることを確認
    const slotsCount = await timeGrid.locator('.slot').count();
    expect(slotsCount).toBe(144);
  });

  test('should correctly label each hour', async ({ page }) => {
    await page.goto('/');

    // 各時刻ラベルを取得し確認
    const hourLabels = page.locator('.hour-label:not(.opacity-0)');
    await expect(hourLabels).toHaveCount(24);

    // 0時から23時まで1時間刻みのラベルを確認
    for (let hour = 0; hour < 24; hour++) {
      const expectedLabel = `${hour.toString().padStart(2, '0')}:00`;
      await expect(hourLabels.nth(hour)).toHaveText(expectedLabel);
    }
  });

});
