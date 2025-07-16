import { test, expect } from '@playwright/test';
import { mockGoogleCalendar } from './helpers';

// Ensure tasks cannot be dropped onto blocked slots

test('blocked slot rejects dropped task', async ({ page, request }) => {
  await mockGoogleCalendar(page);

  // Create a single task via API
  const res = await request.post('/api/tasks', {
    data: {
      title: 'BlockDrag',
      category: 'e2e',
      duration_min: 10,
      duration_raw_min: 10,
      priority: 'A',
    },
  });
  const { id: taskId } = await res.json();

  // Mock schedule generation
  await page.route('**/api/schedule/generate**', route => {
    const body = JSON.stringify({ date: '2025-01-01', slots: new Array(144).fill(0), unplaced: [] });
    route.fulfill({ status: 200, contentType: 'application/json', body });
  });

  // Provide minimal Alpine store implementation
  await page.addInitScript(() => {
    window.Alpine = {
      stores: {},
      store(name, value) {
        if (value !== undefined) this.stores[name] = value;
        return this.stores[name];
      },
    } as any;
    window.dispatchEvent(new Event('alpine:init'));
  });

  await page.goto('/');

  const selector = `[data-task-id="${taskId}"]`;
  const card = page.locator(selector);
  await expect(card).toBeVisible({ timeout: 15000 });

  // Insert a block covering the first slot
  await page.evaluate(() => {
    const store = window.Alpine.store('blocks');
    store.data = [{
      id: 'blk1',
      start_utc: '2025-01-01T00:00:00Z',
      end_utc: '2025-01-01T00:10:00Z',
    }];
  });

  // Generate schedule for 2025-01-01 to apply blocked slots
  await page.evaluate(() => {
    const input = document.getElementById('input-date') as HTMLInputElement;
    input.value = '2025-01-01';
    input.dispatchEvent(new Event('change', { bubbles: true }));
  });
  await page.getByTestId('generate-btn').click();

  const slot = page.locator('[data-slot-index="0"]');
  await expect(slot).toHaveClass(/grid-slot--blocked/);

  const from = await card.boundingBox();
  const to = await slot.boundingBox();
  if (!from || !to) throw new Error('boundingBox retrieval failed');

  await page.mouse.move(from.x + from.width / 2, from.y + from.height / 2);
  await page.mouse.down();
  await page.mouse.move(to.x + to.width / 2, to.y + to.height / 2);
  await page.mouse.up();

  await expect(slot.locator(selector)).toHaveCount(0);
  await expect(page.locator(`#task-pane ${selector}`)).toHaveCount(1);
});
