import { test, expect } from '@playwright/test';

// Import blocks from Sheets via dialog

test('blocks import dialog shows preview count and triggers replace', async ({ page }) => {
  await page.addInitScript(() => {
    // Minimal Alpine store stub
    (window as any).Alpine = {
      stores: {
        blocks: {
          async importPreview() {
            return [{ id: 'b1' }, { id: 'b2' }];
          },
          async importReplace() {
            (window as any).replaceCalled = true;
          },
          data: []
        }
      },
      store(name: string) { return (this as any).stores[name]; }
    } as any;
    window.dispatchEvent(new Event('alpine:init'));
  });

  await page.goto('/');

  await page.locator('[data-tab="blocks-panel"]').click();
  await page.locator('#btn-import-blocks').click();

  const dialog = page.locator('#blocks-import-dialog');
  await expect(dialog).toBeVisible();
  await expect(dialog.locator('#blocks-import-count')).toHaveText('2');

  await dialog.locator('#blocks-import-ok').click();
  await expect(dialog).not.toBeVisible();

  const called = await page.evaluate(() => (window as any).replaceCalled === true);
  expect(called).toBe(true);
});
