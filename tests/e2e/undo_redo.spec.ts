import { test, expect } from '@playwright/test';

test.describe('Undo/Redo', () => {
  test('undoes and redoes a drag operation', async ({ page }) => {
    const data = {
      title: 'Sample Task',
      category: 'general',
      duration_min: 10,
      duration_raw_min: 10,
      priority: 'A'
    };
    await page.request.post('/api/tasks', { data });

    await page.goto('http://localhost:5173');

    const card = page.locator('.task-card').first();
    await expect(card).toBeVisible();

    const slot = page.locator('[data-slot-index="0"]');
    await card.dragTo(slot);
    await expect(slot.locator('.task-card')).toBeVisible();

    await page.getByRole('button', { name: 'Undo' }).click();
    await expect(slot.locator('.task-card')).toHaveCount(0);

    await page.getByRole('button', { name: 'Redo' }).click();
    await expect(slot.locator('.task-card')).toBeVisible();
  });
});
