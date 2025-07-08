import { test, expect } from '@playwright/test';

test('offline schedule loads events without meta', async ({ page }) => {
  await page.route('**/api/calendar**', r =>
    r.fulfill({ status: 200, contentType: 'application/json', body: '[]' })
  );
  await page.route('**/api/tasks**', r =>
    r.fulfill({ status: 200, contentType: 'application/json', body: '[]' })
  );

  await page.goto('/');

  // Insert schedule record lacking events metadata
  await page.evaluate(async () => {
    const db: IDBDatabase = await (window as any).dbReady;
    const date = (document.getElementById('input-date') as HTMLInputElement).value;
    const grid = Array(144).fill(0);
    for (let i = 10; i <= 12; i++) grid[i] = { event_id: 'ev1' };
    await new Promise<void>((resolve, reject) => {
      const tx = db.transaction('schedule', 'readwrite');
      const store = tx.objectStore('schedule');
      const req = store.put({ date, grid, meta: { tasks: {} } });
      req.onsuccess = () => resolve();
      req.onerror = () => reject(req.error);
    });
  });

  await page.route('**/api/schedule/generate**', r => r.abort());
  await page.reload();
  await page.getByTestId('generate-btn').click();

  const slot10 = page.locator('[data-slot-index="10"]');
  const slot11 = page.locator('[data-slot-index="11"]');
  const slot12 = page.locator('[data-slot-index="12"]');

  await expect(slot10).toHaveClass(/bg-gray-200/);
  await expect(slot11).toHaveClass(/border-t-0/);
  await expect(slot11).toHaveClass(/border-b-0/);
  await expect(slot12).toHaveClass(/border-t-0/);
});
