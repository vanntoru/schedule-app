import { test, expect } from '@playwright/test';

// Display toast when Sheets import fails

test('sheets import error shows toast', async ({ page }) => {
  await page.route('**/api/calendar**', route =>
    route.fulfill({ status: 200, contentType: 'application/json', body: '[]' })
  );
  await page.route('**/api/tasks/import', route =>
    route.fulfill({
      status: 422,
      contentType: 'application/json',
      body: JSON.stringify({ detail: 'sheet error' })
    })
  );

  await page.goto('/');
  await page.locator('#btn-import-sheets').click();

  const toast = page.locator('.schedule-toast');
  await expect(toast).toHaveCount(1);
  await expect(toast).toBeVisible();
  await expect(toast).toContainText('sheet error');
});

// Redirect to login on 401 response

test('sheets import 401 redirects to login', async ({ page }) => {
  await page.addInitScript(() => {
    Object.defineProperty(navigator, 'webdriver', { get: () => false });
  });

  await page.route('**/login', route =>
    route.fulfill({ status: 200, contentType: 'text/html', body: 'login page' })
  );
  await page.route('**/api/calendar**', route =>
    route.fulfill({ status: 200, contentType: 'application/json', body: '[]' })
  );
  await page.route('**/api/tasks/import', route =>
    route.fulfill({
      status: 401,
      contentType: 'application/json',
      body: JSON.stringify({ detail: 'missing credentials' })
    })
  );

  await page.goto('/');

  await Promise.all([
    page.waitForURL('**/login'),
    page.locator('#btn-import-sheets').click(),
  ]);

  await expect(page).toHaveURL(/\/login$/);
});
