import { test, expect } from '@playwright/test';

test.setTimeout(60_000);

test('Undo/Redo 動作確認', async ({ page }) => {
  /* ---- Google Calendar API モック ---- */
  await page.route('**/api/calendar**', r =>
    r.fulfill({ status: 200, contentType: 'application/json', body: '[]' })
  );

  await page.goto('http://localhost:5173');

  /* === 1) 前回残りタスクを全削除 ========================== */
  await page.evaluate(async () => {
    const tasks: any[] = await fetch('/api/tasks').then(r => r.json());
    for (const t of tasks) {
      await fetch(`/api/tasks/${t.id}`, { method: 'DELETE' });
    }
  });

  /* === 2) テスト用タスクを追加し、生成された id を取得 ===== */
  const newTask = {
    title: 'E2Eテスト用タスク',
    category: 'テスト',
    duration_min: 10,
    duration_raw_min: 10,
    priority: 'A'
  };

  const created = await page.evaluate(async (t) => {
    const res = await fetch('/api/tasks', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(t)
    });
    if (!res.ok) throw new Error('POST failed');
    return await res.json();
  }, newTask);
  const taskId: string = created.id;

  /* === 3) ページをリロードして描画完了を保証 =============== */
  await Promise.all([
    page.waitForResponse(r => r.url().includes('/api/tasks') && r.status() === 200),
    page.reload()
  ]);

  /* === 4) 正式 id で 1 要素だけ待つ ======================== */
  const selector = `[data-task-id="${taskId}"]`;
  await page.waitForSelector(selector, { timeout: 15000 });
  const taskCard = page.locator(selector);

  /* --- スロット要素を正しい属性で取得 ----------------- */
  const slotBefore = page.locator('[data-slot-index="10"]');
  const slotAfter  = page.locator('[data-slot-index="20"]');

  await slotAfter.scrollIntoViewIfNeeded();
  await expect(slotAfter).toBeVisible({ timeout: 5_000 });

  /* --- ドラッグ操作 --- */
  const from = await taskCard.boundingBox();
  const to   = await slotAfter.boundingBox();
  if (!from || !to) throw new Error('boundingBox 取得失敗');

  await page.mouse.move(from.x + from.width / 2, from.y + from.height / 2);
  await page.mouse.down();
  await page.mouse.move(to.x + to.width / 2, to.y + to.height / 2);
  await page.mouse.up();

  await expect(slotAfter.locator(selector)).toHaveCount(1);

  /* --- Undo / Redo --- */
  await page.keyboard.press('Control+Z');

  await expect(slotBefore.locator(selector)).toHaveCount(0);

  // 🔴ここを実際のDOMに合わせて変更してください
  const sidePanel = page.locator('#task-pane');
  await expect(sidePanel.locator(selector)).toHaveCount(1);

  await page.keyboard.press('Control+Y');
  await expect(slotAfter.locator(selector)).toHaveCount(1);
});
