import { test, expect } from '@playwright/test';

test('header and toolbar buttons hidden when printing', async ({ page }) => {
  await page.goto('/');

  const header = page.locator('header');
  await expect(header).toBeVisible();

  const buttons = header.locator('button');
  await expect(buttons).toHaveCount(3);
  for (let i = 0; i < 3; i++) {
    await expect(buttons.nth(i)).toBeVisible();
  }

  await page.emulateMedia({ media: 'print' });

  await expect(header).toBeHidden();
  for (let i = 0; i < 3; i++) {
    await expect(buttons.nth(i)).toBeHidden();
  }
});
