import { test, expect } from '@playwright/test';
import { mockGoogleCalendar } from './helpers';

// Drag a task to one slot, move it to another, then undo/redo

test('card moved between slots supports undo/redo', async ({ page, request }) => {
  await mockGoogleCalendar(page);

  // Create task via API
  const res = await request.post('/api/tasks', {
    data: {
      title: 'MoveBetweenSlots',
      category: 'e2e',
      duration_min: 10,
      duration_raw_min: 10,
      priority: 'A',
    },
  });
  const { id: taskId } = await res.json();

  await page.goto('/');

  const selector = `[data-task-id="${taskId}"]`;
  const card = page.locator(selector);
  await expect(card).toBeVisible({ timeout: 15000 });

  const slotA = page.locator('[data-slot-index="5"]');
  const slotB = page.locator('[data-slot-index="10"]');
  await slotB.scrollIntoViewIfNeeded();
  await expect(slotB).toBeVisible();

  // Drag card from side panel to slot A
  let from = await card.boundingBox();
  let to = await slotA.boundingBox();
  if (!from || !to) throw new Error('boundingBox retrieval failed');
  await page.mouse.move(from.x + from.width / 2, from.y + from.height / 2);
  await page.mouse.down();
  await page.mouse.move(to.x + to.width / 2, to.y + to.height / 2);
  await page.mouse.up();

  await expect(slotA.locator(selector)).toHaveCount(1);
  await expect(page.locator(`#task-pane ${selector}`)).toHaveCount(0);

  // Drag card from slot A to slot B
  from = await card.boundingBox();
  to = await slotB.boundingBox();
  if (!from || !to) throw new Error('boundingBox retrieval failed');
  await page.mouse.move(from.x + from.width / 2, from.y + from.height / 2);
  await page.mouse.down();
  await page.mouse.move(to.x + to.width / 2, to.y + to.height / 2);
  await page.mouse.up();

  await expect(slotB.locator(selector)).toHaveCount(1);
  await expect(slotA.locator(selector)).toHaveCount(0);

  // Undo returns card to slot A
  await page.keyboard.press('Control+Z');
  await expect(slotA.locator(selector)).toHaveCount(1);
  await expect(slotB.locator(selector)).toHaveCount(0);

  // Redo moves card back to slot B
  await page.keyboard.press('Control+Y');
  await expect(slotB.locator(selector)).toHaveCount(1);
  await expect(slotA.locator(selector)).toHaveCount(0);
});

