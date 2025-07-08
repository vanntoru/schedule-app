import { test, expect } from '@playwright/test';

test('UI elements hidden in print media', async ({ page }) => {
  const response = await page.goto('/');
  expect(response?.status()).toBe(200);

  await page.emulateMedia({ media: 'print' });

  await expect(page.locator('header')).toBeHidden();

  for (const selector of ['#app-header', '#side-pane']) {
    const loc = page.locator(selector);
    if (await loc.count() > 0) {
      await expect(loc).toBeHidden();
    } else {
      await expect(loc).toHaveCount(0);
    }
  }

  for (const selector of ['.toolbar', 'button', '.no-print']) {
    const loc = page.locator(selector);
    if (await loc.count() > 0) {
      await expect(loc).toBeHidden();
    } else {
      await expect(loc).toHaveCount(0);
    }
  }
});
