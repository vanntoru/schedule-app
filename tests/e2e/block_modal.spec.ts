import { test, expect } from '@playwright/test';

// Verify floating add block button opens the modal

test('add block button opens modal', async ({ page }) => {
  await page.goto('/');

  const btn = page.locator('#btn-add-block');
  await expect(btn).toBeVisible();
  await expect(btn).toHaveClass(/fixed/);
  await expect(btn).toHaveClass(/bottom-4/);
  await expect(btn).toHaveClass(/right-4/);

  await btn.click();
  await expect(page.locator('#block-modal')).toBeVisible();
});
