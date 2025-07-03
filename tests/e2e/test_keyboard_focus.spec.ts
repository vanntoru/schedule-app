/* 色ではなく「リング幅 2 px」が入っているかをテスト */

import { test, expect } from '@playwright/test';

test('keyboard focus traverses to first task card', async ({ page }) => {
  // --- API モック ---
  await page.route('**/api/tasks', route =>
    route.fulfill({
      status: 200,
      contentType: 'application/json',
      body: JSON.stringify([
        {
          id: 't1',
          title: 'Sample Task',
          category: 'misc',
          duration_min: 10,
          duration_raw_min: 10,
          priority: 'A'
        }
      ])
    })
  );

  // --- アプリ起動 ---
  await page.goto('http://localhost:5173');
  await page.waitForSelector('.task-card');       // DOM に出るまで待つ

  // --- Tab で task-card にフォーカスさせる ---
  for (let i = 0; i < 40; i++) {
    const onCard = await page.evaluate(() =>
      document.activeElement?.classList.contains('task-card')
    );
    if (onCard) break;
    await page.keyboard.press('Tab');
  }

  // 1. task-card がアクティブ
  expect(
    await page.evaluate(() =>
      document.activeElement?.classList.contains('task-card')
    )
  ).toBeTruthy();

  // 2. フォーカスリング（box‑shadow）の幅 2 px を確認
  const shadow = await page.evaluate(
    () => getComputedStyle(document.activeElement!).boxShadow
  );
  expect(shadow).toMatch(/0px 0px 0px 2px/);
});
