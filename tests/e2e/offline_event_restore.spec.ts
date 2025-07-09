import { test, expect } from '@playwright/test';

// Ensure offline event metadata spanning busy cells is reconstructed

test('offline restore groups busy slots after event', async ({ page }) => {
  await page.route('**/api/calendar**', r =>
    r.fulfill({ status: 200, contentType: 'application/json', body: '[]' })
  );

  await page.goto('/');

  await page.evaluate(async () => {
    const db = await (window as any).dbReady;
    const date = (document.getElementById('input-date') as HTMLInputElement).value;

    const grid: any[] = new Array(144).fill(0);
    grid[0] = { event_id: 'ev1' };
    for (let i = 1; i < 6; i++) {
      grid[i] = { busy: true };
    }
    const record = { date, grid, meta: { tasks: {}, events: {} } };
    await new Promise<void>(resolve => {
      const tx = db.transaction('schedule', 'readwrite');
      tx.objectStore('schedule').put(record);
      tx.oncomplete = () => resolve();
      tx.onerror = () => resolve();
    });
  });

  await page.route('**/api/schedule/generate**', r => r.abort());
  await page.reload();
  await page.getByTestId('generate-btn').click();

  for (let i = 0; i < 6; i++) {
    const slot = page.locator(`[data-slot-index="${i}"]`);
    await expect(slot).toHaveClass(/grid-slot--busy/);
  }
});
