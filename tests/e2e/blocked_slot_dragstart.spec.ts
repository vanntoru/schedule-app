import { test, expect } from '@playwright/test';
import { mockGoogleCalendar } from './helpers';

// Ensure dragging from a blocked slot is prevented

test('blocked slot prevents dragstart', async ({ page, request }) => {
  await mockGoogleCalendar(page);

  const res = await request.post('/api/tasks', {
    data: {
      title: 'BlockDragStart',
      category: 'e2e',
      duration_min: 10,
      duration_raw_min: 10,
      priority: 'A',
    },
  });
  const { id: taskId } = await res.json();

  await page.route('**/api/schedule/generate**', route => {
    const body = JSON.stringify({ date: '2025-01-01', slots: new Array(144).fill(0), unplaced: [] });
    route.fulfill({ status: 200, contentType: 'application/json', body });
  });

  await page.addInitScript(() => {
    window.Alpine = {
      stores: {},
      store(name: string, value?: any) {
        if (value !== undefined) this.stores[name] = value;
        return this.stores[name];
      },
    } as any;
  });

  await page.goto('/');

  await page.evaluate(() => {
    window.Alpine.store('blocks', { data: [] });
  });

  const selector = `[data-task-id="${taskId}"]`;
  const card = page.locator(selector);
  await expect(card).toBeVisible({ timeout: 15000 });

  const slot0 = page.locator('.slot[data-slot-index="0"]');
  let from = await card.boundingBox();
  let to = await slot0.boundingBox();
  if (!from || !to) throw new Error('boundingBox retrieval failed');

  await page.mouse.move(from.x + from.width / 2, from.y + from.height / 2);
  await page.mouse.down();
  await page.mouse.move(to.x + to.width / 2, to.y + to.height / 2);
  await page.mouse.up();

  await expect(slot0.locator(selector)).toHaveCount(1);

  await page.evaluate(() => {
    const store = window.Alpine.store('blocks');
    store.data = [{
      id: 'blk1',
      start_utc: '2025-01-01T00:00:00Z',
      end_utc: '2025-01-01T00:10:00Z',
    }];
  });

  await page.evaluate(() => {
    const input = document.getElementById('input-date') as HTMLInputElement;
    input.value = '2025-01-01';
    input.dispatchEvent(new Event('change', { bubbles: true }));
  });
  await page.getByTestId('generate-btn').click();

  await expect(slot0).toHaveClass(/grid-slot--blocked/);

  const slot1 = page.locator('.slot[data-slot-index="1"]');
  from = await card.boundingBox();
  to = await slot1.boundingBox();
  if (!from || !to) throw new Error('boundingBox retrieval failed');

  await page.mouse.move(from.x + from.width / 2, from.y + from.height / 2);
  await page.mouse.down();
  await page.mouse.move(to.x + to.width / 2, to.y + to.height / 2);
  await page.mouse.up();

  await expect(slot0.locator(selector)).toHaveCount(1);
  await expect(slot1.locator(selector)).toHaveCount(0);
});
