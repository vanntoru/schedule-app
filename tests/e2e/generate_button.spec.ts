import { test, expect } from '@playwright/test';

test('generate button triggers schedule API', async ({ page }) => {
  // Stub calendar API to avoid 401 redirect during test
  await page.route('**/api/calendar**', r =>
    r.fulfill({ status: 200, contentType: 'application/json', body: '[]' })
  );

  await page.goto('/');

  const [req] = await Promise.all([
    page.waitForRequest(r => r.url().includes('/api/schedule/generate')),
    page.getByTestId('generate-btn').click()
  ]);

  expect(req.method()).toBe('POST');
});
