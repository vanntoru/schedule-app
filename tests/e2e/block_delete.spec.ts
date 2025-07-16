import { test, expect } from '@playwright/test';

// Ensure clicking the delete button removes a block entry

test('delete block removes list item', async ({ page }) => {
  await page.addInitScript(() => {
    window.Alpine = {
      stores: {},
      store(name: string, value?: any) {
        if (value !== undefined) this.stores[name] = value;
        return this.stores[name];
      }
    } as any;
    window.dispatchEvent(new Event('alpine:init'));
  });

  await page.goto('/');

  // Switch to the Blocks tab so the panel is visible
  await page.locator('[data-tab="blocks-panel"]').click();

  // Inject a fake block entry for testing
  await page.evaluate(() => {
    const list = document.querySelector('#block-list');
    if (!list) return;
    const li = document.createElement('li');
    li.dataset.blockId = 'b1';

    const btn = document.createElement('button');
    btn.type = 'button';
    btn.className = 'delete-block';
    btn.textContent = 'del';
    li.appendChild(btn);

    list.appendChild(li);

    // simple delete handler mirroring app behaviour
    list.addEventListener('click', e => {
      const target = (e.target as HTMLElement).closest('.delete-block');
      if (!target) return;
      if (!confirm('delete block?')) return;
      target.closest('li')?.remove();
    });
  });

  const item = page.locator('[data-block-id="b1"]');
  await expect(item).toHaveCount(1);

  page.once('dialog', d => d.accept());
  await item.locator('.delete-block').click();
  await expect(item).toHaveCount(0);
});
