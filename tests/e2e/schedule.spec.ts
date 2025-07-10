import { test, expect } from '@playwright/test';

test('top page loads with correct title', async ({ page }) => {
  await page.goto('/');
  await expect(page).toHaveTitle('1-Day Schedule');
});
