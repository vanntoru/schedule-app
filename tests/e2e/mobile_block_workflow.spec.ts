import { test, expect, devices } from '@playwright/test';
import { mockGoogleCalendar, mockBlocks } from './helpers';

// Mobile scenario for creating, updating and deleting blocks

test.use({ ...devices['Pixel 5'] });

test('mobile block workflow via modal form', async ({ page, request }) => {
  // Prevent calendar redirects
  await mockGoogleCalendar(page);

  // Minimal Alpine.js stub and DOM helpers before scripts run
  await page.addInitScript(() => {
    window.Alpine = {
      stores: {},
      store(name: string, value?: any) {
        if (value !== undefined) this.stores[name] = value;
        return this.stores[name];
      },
    } as any;

    window.addEventListener('blocks:created', (e: any) => {
      const block = e.detail;
      const list = document.querySelector('#block-list');
      if (!list) return;
      const li = document.createElement('li');
      li.dataset.blockId = block.id;
      li.innerHTML =
        `<span class="block-title">${block.title || 'Block'}</span>` +
        '<button type="button" class="edit-block">edit</button>' +
        '<button type="button" class="delete-block">del</button>';
      list.appendChild(li);
    });
    window.addEventListener('blocks:updated', (e: any) => {
      const block = e.detail;
      const item = document.querySelector(`[data-block-id="${block.id}"]`);
      item?.querySelector('.block-title')?.replaceWith(Object.assign(document.createElement('span'), { className: 'block-title', textContent: block.title || 'Block' }));
    });
    window.addEventListener('blocks:removed', (e: any) => {
      const id = e.detail;
      document.querySelector(`[data-block-id="${id}"]`)?.remove();
    });

    window.dispatchEvent(new Event('alpine:init'));
  });

  // Clear existing blocks
  const res = await request.get('/api/blocks');
  const blocks = await res.json();
  for (const b of blocks) {
    await request.delete(`/api/blocks/${b.id}`);
  }

  await mockBlocks(page);

  await page.goto('/');

  // Show the Blocks panel
  await page.locator('[data-tab="blocks-panel"]').click();

  // ---- Create ----
  await page.locator('#btn-add-block').click();
  await page.fill('#block-title', 'E2E Block');
  await page.fill('#block-start', '2025-01-01T00:00');
  await page.fill('#block-end', '2025-01-01T00:10');

  const [postReq] = await Promise.all([
    page.waitForRequest(r => r.url().endsWith('/api/blocks') && r.method() === 'POST'),
    page.locator('#block-form button[type=submit]').click(),
  ]);
  expect(postReq.method()).toBe('POST');

  const listResp = await request.get('/api/blocks');
  const [created] = await listResp.json();
  const blockId = created.id;

  const item = page.locator(`[data-block-id="${blockId}"]`);
  await expect(item).toHaveCount(1);

  // ---- Update ----
  await item.locator('.edit-block').click();
  await page.fill('#block-title', 'Updated Block');

  const [putReq] = await Promise.all([
    page.waitForRequest(r => r.url().includes(`/api/blocks/${blockId}`) && r.method() === 'PUT'),
    page.locator('#block-form button[type=submit]').click(),
  ]);
  expect(putReq.method()).toBe('PUT');
  await expect(item.locator('.block-title')).toHaveText('Updated Block');

  // ---- Delete ----
  page.once('dialog', d => d.accept());
  const [delReq] = await Promise.all([
    page.waitForRequest(r => r.url().includes(`/api/blocks/${blockId}`) && r.method() === 'DELETE'),
    item.locator('.delete-block').click(),
  ]);
  expect(delReq.method()).toBe('DELETE');
  await expect(page.locator(`[data-block-id="${blockId}"]`)).toHaveCount(0);
});
