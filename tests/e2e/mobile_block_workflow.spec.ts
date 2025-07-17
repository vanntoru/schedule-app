import { test, expect, devices } from '@playwright/test';
import { pseudoLogin, mockGoogleCalendar } from './helpers';

test.use({ ...devices['iPhone 11'] });

test('mobile block workflow via modal form', async ({ page, request }) => {
  await mockGoogleCalendar(page);
  await pseudoLogin(page);

  // Remove existing blocks
  const existing = await request.get('/api/blocks');
  const blocks = await existing.json();
  for (const b of blocks) {
    await request.delete(`/api/blocks/${b.id}`);
  }

  await page.goto('/');

  // Show blocks panel
  await page.locator('[data-tab="blocks-panel"]').click();

  // Create new block
  await page.locator('#btn-add-block').click();
  await page.fill('#block-title', 'Mobile Block');
  await page.fill('#block-start', '2025-01-01T00:00');
  await page.fill('#block-end', '2025-01-01T00:10');

  const [postReq] = await Promise.all([
    page.waitForRequest(r => r.url().endsWith('/api/blocks') && r.method() === 'POST'),
    page.locator('#block-form button[type=submit]').click(),
  ]);
  expect(postReq.method()).toBe('POST');

  const item = page.locator('#block-list > li');
  await expect(item).toHaveCount(1);

  const blockId = await item.getAttribute('data-block-id');
  expect(blockId).toBeTruthy();

  // Update block
  await item.locator('.edit-block').click();
  await page.fill('#block-title', 'Updated Block');

  const [putReq] = await Promise.all([
    page.waitForRequest(r => r.url().includes(`/api/blocks/${blockId}`) && r.method() === 'PUT'),
    page.locator('#block-form button[type=submit]').click(),
  ]);
  expect(putReq.method()).toBe('PUT');

  const updated = page.locator(`[data-block-id="${blockId}"]`);
  await expect(updated).toHaveCount(1);

  // Delete block
  page.once('dialog', d => d.accept());
  const [delReq] = await Promise.all([
    page.waitForRequest(r => r.url().includes(`/api/blocks/${blockId}`) && r.method() === 'DELETE'),
    updated.locator('.delete-block').click(),
  ]);
  expect(delReq.method()).toBe('DELETE');
  await expect(page.locator(`[data-block-id="${blockId}"]`)).toHaveCount(0);
});
