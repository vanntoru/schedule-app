import { test, expect } from '@playwright/test';

test('offline cached events display placeholder title', async ({ page }) => {
  await page.route('**/api/calendar**', r =>
    r.fulfill({ status: 200, contentType: 'application/json', body: '[]' })
  );

  await page.goto('/');

  await page.evaluate(async () => {
    const db = await (window as any).dbReady;
    const tx = db.transaction('schedule', 'readwrite');
    const store = tx.objectStore('schedule');
    const grid = Array(144).fill(0);
    for (let i = 54; i < 60; i++) {
      grid[i] = { event_id: 'ev1' };
    }
    store.put({ date: '2025-01-01', grid, meta: { tasks: {}, events: {} } });
    return new Promise<void>(resolve => { tx.oncomplete = () => resolve(); });
  });

  await page.route('**/api/schedule/generate**', r => r.abort());

  await page.reload();
  await page.fill('#input-date', '2025-01-01');
  await page.getByTestId('generate-btn').click();

  const firstSlot = page.locator('[data-slot-index="54"]');
  await expect(firstSlot).toHaveText('予定あり');

  const record = await page.evaluate(async () => {
    const db = await (window as any).dbReady;
    const req = db.transaction('schedule', 'readonly').objectStore('schedule').get('2025-01-01');
    return await new Promise<any>(resolve => { req.onsuccess = () => resolve(req.result); });
  });
  expect(record.meta.events['ev1'].title).toBe('予定あり');
});
