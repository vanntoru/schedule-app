import { test, expect } from '@playwright/test';

// Ensure clicking Tasks/Blocks tabs toggles the panels

test('side pane tabs toggle visibility', async ({ page }) => {
  await page.goto('/');

  const taskPane = page.locator('#task-pane');
  const blocksPane = page.locator('#blocks-panel');

  await expect(taskPane).toBeVisible();
  await expect(blocksPane).toBeHidden();

  await page.locator('[data-tab="blocks-panel"]').click();
  await expect(blocksPane).toBeVisible();
  await expect(taskPane).toBeHidden();

  await page.locator('[data-tab="task-pane"]').click();
  await expect(taskPane).toBeVisible();
  await expect(blocksPane).toBeHidden();
});
