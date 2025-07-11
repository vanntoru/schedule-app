import { test, expect } from '@playwright/test';

test('header and toolbar buttons hidden when printing', async ({ page }) => {
  await page.goto('/');

  const header = page.locator('header');
  await expect(header).toBeVisible();

  const buttons = header.locator('button');
  await expect(buttons).toHaveCount(5);
  for (let i = 0; i < await buttons.count(); i++) {
    await expect(buttons.nth(i)).toBeVisible();
  }

  for (const sel of ['.toolbar', '.no-print']) {
    const nodes = page.locator(sel);
    for (let i = 0; i < await nodes.count(); i++) {
      await expect(nodes.nth(i)).toBeVisible();
    }
  }

  await page.emulateMedia({ media: 'print' });

  await expect(header).toBeHidden();

  for (let i = 0; i < await buttons.count(); i++) {
    await expect(buttons.nth(i)).toBeHidden();
  }

  for (const sel of ['.toolbar', '.no-print']) {
    const nodes = page.locator(sel);
    for (let i = 0; i < await nodes.count(); i++) {
      await expect(nodes.nth(i)).toBeHidden();
    }
  }
});
