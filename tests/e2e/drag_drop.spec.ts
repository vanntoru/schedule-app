import { test, expect } from '@playwright/test';
import { mockGoogleCalendar } from './helpers';

// Drag and drop a task from the side panel onto the time grid

test('task card can be dragged to a slot', async ({ page, request }) => {
  // Mock Google Calendar API to avoid OAuth redirects
  await mockGoogleCalendar(page);

  // Create a task via the API and capture its ID
  const res = await request.post('/api/tasks', {
    data: {
      title: 'DragDropTask',
      category: 'e2e',
      duration_min: 10,
      duration_raw_min: 10,
      priority: 'A'
    }
  });
  const created = await res.json();
  const taskId = created.id as string;

  // Load the page and wait for the task card to appear
  await page.goto('/');
  const selector = `[data-task-id="${taskId}"]`;
  const card = page.locator(selector);
  await expect(card).toBeVisible({ timeout: 15000 });

  // Locate target slot
  const slot = page.locator('[data-slot-index="15"]');
  await slot.scrollIntoViewIfNeeded();
  await expect(slot).toBeVisible();

  // Drag the card using mouse actions
  const from = await card.boundingBox();
  const to = await slot.boundingBox();
  if (!from || !to) throw new Error('boundingBox retrieval failed');

  await page.mouse.move(from.x + from.width / 2, from.y + from.height / 2);
  await page.mouse.down();
  await page.mouse.move(to.x + to.width / 2, to.y + to.height / 2);
  await page.mouse.up();

  // Verify the card resides in the slot and not in the side panel
  await expect(page.locator(`[data-slot-index="15"] ${selector}`)).toHaveCount(1);
  await expect(page.locator(`#task-pane ${selector}`)).toHaveCount(0);
});

