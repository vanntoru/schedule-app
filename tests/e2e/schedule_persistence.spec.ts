import { test, expect } from '@playwright/test';

test('schedule saved and restored from IndexedDB', async ({ page, request }) => {
  await page.route('**/api/calendar**', r =>
    r.fulfill({ status: 200, contentType: 'application/json', body: '[]' })
  );

  await request.post('/api/tasks', {
    data: {
      title: 'Persisted Task',
      category: 'e2e',
      duration_min: 10,
      duration_raw_min: 10,
      priority: 'A'
    }
  });

  await page.goto('/');
  await page.getByTestId('generate-btn').click();

  const busySlot = page.locator('.slot.bg-green-200');
  await expect(busySlot.first()).toBeVisible();

  const record = await page.evaluate(async () => {
    const db = await (window as any).dbReady;
    const date = (document.getElementById('input-date') as HTMLInputElement).value;
    return await new Promise<any>(resolve => {
      const tx = db.transaction('schedule', 'readonly');
      const req = tx.objectStore('schedule').get(date);
      req.onsuccess = () => resolve(req.result);
      req.onerror = () => resolve(null);
    });
  });

  expect(record).not.toBeNull();
  expect(Array.isArray(record.grid)).toBe(true);

  await page.route('**/api/schedule/generate**', r => r.abort());
  await page.reload();
  await page.getByTestId('generate-btn').click();

  await expect(busySlot.first()).toBeVisible();
});
