import { test, expect } from '@playwright/test';

// Deleting a block from the list triggers confirmation and removal

test('delete block removes list item', async ({ page }) => {
  await page.goto('/');

  // Wait for Alpine store to be ready then inject a block
  await page.waitForFunction(() => (window as any).Alpine && (window as any).Alpine.store('blocks'));
  await page.evaluate(() => {
    const store = (window as any).Alpine!.store('blocks');
    store.data = [{
      id: 'b1',
      title: 'Demo Block',
      start_utc: '2025-01-01T00:00:00Z',
      end_utc: '2025-01-01T01:00:00Z'
    }];
  });

  await page.locator('[data-tab="blocks-panel"]').click();

  const item = page.locator('#block-list li').filter({ hasText: 'Demo Block' });
  await expect(item).toBeVisible({ timeout: 5000 });

  page.once('dialog', d => d.accept());
  await item.locator('.delete-block').click();

  await expect(page.locator('#block-list li')).toHaveCount(0);
});
