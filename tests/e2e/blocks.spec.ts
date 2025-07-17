import { test, expect } from '@playwright/test';
import { mockGoogleCalendar } from './helpers';

// Full block workflow: create -> grid update -> delete -> Sheets import

test('block CRUD and import flow updates grid on mobile', async ({ page, request }) => {
  await mockGoogleCalendar(page);

  // Ensure server has no blocks
  const existing = await request.get('/api/blocks');
  for (const b of await existing.json()) {
    await request.delete(`/api/blocks/${b.id}`);
  }

  // Return a fixed grid for schedule generation
  await page.route('**/api/schedule/generate**', route => {
    const body = JSON.stringify({ date: '2025-01-01', slots: new Array(144).fill(0), unplaced: [] });
    route.fulfill({ status: 200, contentType: 'application/json', body });
  });

  const sheetBlocks = [
    { id: 's1', start_utc: '2025-01-01T02:00:00Z', end_utc: '2025-01-01T02:10:00Z' },
  ];

  await page.route('**/api/blocks/import', async route => {
    if (route.request().method() === 'GET') {
      route.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify(sheetBlocks) });
    } else {
      const resp = await page.request.get('/api/blocks');
      for (const b of await resp.json()) {
        await page.request.delete(`/api/blocks/${b.id}`);
      }
      for (const b of sheetBlocks) {
        await page.request.post('/api/blocks', { data: { start_utc: b.start_utc, end_utc: b.end_utc } });
      }
      route.fulfill({ status: 204 });
    }
  });

  // Minimal Alpine stub
  await page.addInitScript(() => {
    window.Alpine = {
      stores: {},
      store(name, value) {
        if (value !== undefined) this.stores[name] = value;
        return this.stores[name];
      },
    } as any;
  });

  // Mobile viewport
  await page.setViewportSize({ width: 375, height: 800 });
  await page.goto('/');
  await page.evaluate(() => window.dispatchEvent(new Event('alpine:init')));

  // Custom store methods with DOM updates
  await page.evaluate(() => {
    const store = window.Alpine.store('blocks', {} as any);
    store.data = [];
    store.fetch = async function () {
      const res = await fetch('/api/blocks');
      const blocks = await res.json();
      this.data = blocks;
      const list = document.getElementById('block-list');
      if (list) {
        list.innerHTML = '';
        for (const b of blocks) {
          const li = document.createElement('li');
          li.dataset.blockId = b.id;
          li.innerHTML = '<button type="button" class="delete-block">del</button>';
          list.appendChild(li);
        }
      }
      window.dispatchEvent(new CustomEvent('blocks:fetched', { detail: blocks }));
    };
    store.create = async function (payload) {
      const res = await fetch('/api/blocks', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(payload),
      });
      const block = await res.json();
      this.data.push(block);
      const li = document.createElement('li');
      li.dataset.blockId = block.id;
      li.innerHTML = '<button type="button" class="delete-block">del</button>';
      document.getElementById('block-list')?.appendChild(li);
      window.dispatchEvent(new CustomEvent('blocks:created', { detail: block }));
    };
    store.remove = async function (id) {
      await fetch(`/api/blocks/${id}`, { method: 'DELETE' });
      this.data = this.data.filter((b) => b.id !== id);
      document.querySelector(`[data-block-id="${id}"]`)?.remove();
      window.dispatchEvent(new CustomEvent('blocks:removed', { detail: id }));
    };
    store.importPreview = async function () {
      const res = await fetch('/api/blocks/import');
      return res.json();
    };
    store.importReplace = async function () {
      await fetch('/api/blocks/import', { method: 'POST' });
      await this.fetch();
      window.dispatchEvent(new CustomEvent('blocks:import-replace'));
      const input = document.getElementById('input-date');
      const ymd = input ? (input as HTMLInputElement).value : '';
      if (ymd) {
        const evt = new Event('change', { bubbles: true });
        input?.dispatchEvent(evt);
      }
    };
  });
  await page.evaluate(() => window.Alpine.store('blocks').fetch());

  // set date and generate initial grid
  await page.evaluate(() => {
    const input = document.getElementById('input-date') as HTMLInputElement;
    input.value = '2025-01-01';
    input.dispatchEvent(new Event('change', { bubbles: true }));
  });
  await page.getByTestId('generate-btn').click();

  const slot0 = page.locator('[data-slot-index="0"]');
  await expect(slot0).not.toHaveClass(/grid-slot--blocked/);

  await page.locator('[data-tab="blocks-panel"]').click();

  // --- Create block ---
  await page.locator('#btn-add-block').click();
  await page.fill('#block-start', '2025-01-01T00:00');
  await page.fill('#block-end', '2025-01-01T00:10');
  const [post] = await Promise.all([
    page.waitForRequest(r => r.url().endsWith('/api/blocks') && r.method() === 'POST'),
    page.locator('#block-form button[type=submit]').click(),
  ]);
  expect(post.method()).toBe('POST');
  await expect(slot0).toHaveClass(/grid-slot--blocked/);

  const item = page.locator('#block-list [data-block-id]');
  await expect(item).toHaveCount(1);

  // --- Delete block ---
  page.once('dialog', d => d.accept());
  const id = await item.getAttribute('data-block-id');
  const [delReq] = await Promise.all([
    page.waitForRequest(r => r.url().includes(`/api/blocks/${id}`) && r.method() === 'DELETE'),
    item.locator('.delete-block').click(),
  ]);
  expect(delReq.method()).toBe('DELETE');
  await expect(item).toHaveCount(0);
  await expect(slot0).not.toHaveClass(/grid-slot--blocked/);

  // --- Import from Sheets ---
  const [previewReq] = await Promise.all([
    page.waitForRequest(r => r.url().includes('/api/blocks/import') && r.method() === 'GET'),
    page.locator('#btn-import-blocks').click(),
  ]);
  expect(previewReq.method()).toBe('GET');
  page.once('dialog', d => d.accept());
  const [postImport] = await Promise.all([
    page.waitForRequest(r => r.url().includes('/api/blocks/import') && r.method() === 'POST'),
    page.waitForResponse(r => r.url().includes('/api/schedule/generate')),
  ]);
  expect(postImport.method()).toBe('POST');

  const slot12 = page.locator('[data-slot-index="12"]');
  await expect(slot12).toHaveClass(/grid-slot--blocked/);
  await expect(page.locator('#block-list [data-block-id]')).toHaveCount(1);

  // no horizontal overflow at 375px
  const overflow = await page.evaluate(() => document.body.scrollWidth > window.innerWidth);
  expect(overflow).toBeFalsy();
});
