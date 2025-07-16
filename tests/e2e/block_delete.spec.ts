import { test, expect } from '@playwright/test';

// Deleting a block from the list triggers confirmation and removal

test('delete block removes list item', async ({ page }) => {
  await page.goto('/');

  // Ensure a block exists via Alpine store
  await page.evaluate(() => {
    const store = window.Alpine?.store('blocks');
    if (store) {
      store.data = [{
        id: 'b1',
        title: 'Demo Block',
        start_utc: '2025-01-01T00:00:00Z',
        end_utc: '2025-01-01T01:00:00Z'
      }];
    }
  });

  await page.locator('[data-tab="blocks-panel"]').click();

  const item = page.locator('#block-list li').filter({ hasText: 'Demo Block' });
  await expect(item).toBeVisible();

  page.once('dialog', d => d.accept());
  await item.locator('.delete-block').click();

  await expect(page.locator('#block-list li')).toHaveCount(0);
});
