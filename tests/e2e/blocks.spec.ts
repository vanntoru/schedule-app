import { test, expect } from '@playwright/test';

// Verify blocks panel workflow and import functionality

test('blocks panel create/delete/import updates grid', async ({ page, request }) => {
  // --- Clear existing blocks via API ---
  let res = await request.get('/api/blocks');
  expect(res.ok()).toBeTruthy();
  const existing = await res.json();
  for (const b of existing) {
    const del = await request.delete(`/api/blocks/${b.id}`);
    expect(del.ok()).toBeTruthy();
  }
  res = await request.get('/api/blocks');
  expect(await res.json()).toEqual([]);

  // --- Network stubs ---
  await page.route('**/api/calendar**', r =>
    r.fulfill({ status: 200, contentType: 'application/json', body: '[]' })
  );

  // predictable schedule grid
  await page.route('**/api/schedule/generate**', route => {
    const body = JSON.stringify({ date: '2025-01-01', slots: new Array(144).fill(0), unplaced: [] });
    route.fulfill({ status: 200, contentType: 'application/json', body });
  });

  const serverBlocks: any[] = [];
  const imported = [{
    id: 'imp1',
    start_utc: '2025-01-01T00:00:00Z',
    end_utc: '2025-01-01T00:10:00Z',
  }];

  // stub /api/blocks CRUD
  await page.route('**/api/blocks**', async route => {
    const { method, url } = route.request();
    if (method === 'GET' && url.endsWith('/api/blocks')) {
      await route.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify(serverBlocks) });
      return;
    }
    if (method === 'POST' && url.endsWith('/api/blocks')) {
      const payload = JSON.parse(route.request().postData() || '{}');
      const block = { id: `b${serverBlocks.length + 1}`, ...payload };
      serverBlocks.push(block);
      await route.fulfill({ status: 201, contentType: 'application/json', body: JSON.stringify(block) });
      return;
    }
    if (method === 'DELETE') {
      const m = url.match(/\/api\/blocks\/(.+)$/);
      if (m) {
        const idx = serverBlocks.findIndex(b => b.id === m[1]);
        if (idx !== -1) serverBlocks.splice(idx, 1);
      }
      await route.fulfill({ status: 204 });
      return;
    }
    await route.continue();
  });

  // stub import preview & replace
  await page.route('**/api/blocks/import', async route => {
    if (route.request().method() === 'GET') {
      await route.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify(imported) });
    } else {
      serverBlocks.splice(0, serverBlocks.length, ...imported);
      await route.fulfill({ status: 204 });
    }
  });

  // ---- Alpine store stub ----
  await page.addInitScript(() => {
    window.Alpine = {
      stores: {},
      store(name: string, value?: any) {
        if (value !== undefined) this.stores[name] = value;
        return this.stores[name];
      },
    } as any;
    window.dispatchEvent(new Event('alpine:init'));
  });

  await page.goto('/');

  // define blocks store after scripts load
  await page.evaluate(() => {
    window.Alpine.store('blocks', {
      data: [],
      async fetch() {
        const res = await fetch('/api/blocks');
        this.data = await res.json();
        window.dispatchEvent(new CustomEvent('blocks:fetched', { detail: this.data }));
      },
      async create(payload: any) {
        const res = await fetch('/api/blocks', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify(payload),
        });
        const block = await res.json();
        this.data.push(block);
        window.dispatchEvent(new CustomEvent('blocks:created', { detail: block }));
      },
      async remove(id: string) {
        await fetch(`/api/blocks/${id}`, { method: 'DELETE' });
        this.data = this.data.filter((b: any) => b.id !== id);
        window.dispatchEvent(new CustomEvent('blocks:removed', { detail: id }));
      },
      async importPreview() {
        const res = await fetch('/api/blocks/import');
        return res.json();
      },
      async importReplace() {
        await fetch('/api/blocks/import', { method: 'POST' });
        await this.fetch();
        window.dispatchEvent(new CustomEvent('blocks:import-replace'));
      },
    });
  });

  // set schedule date and generate grid
  await page.evaluate(() => {
    const input = document.getElementById('input-date') as HTMLInputElement;
    input.value = '2025-01-01';
    input.dispatchEvent(new Event('change', { bubbles: true }));
  });

  const [genReq] = await Promise.all([
    page.waitForRequest(r => r.url().includes('/api/schedule/generate')),
    page.getByTestId('generate-btn').click(),
  ]);
  expect(genReq.method()).toBe('POST');

  // ---- create block via modal ----
  await page.locator('[data-tab="blocks-panel"]').click();
  await expect(page.locator('#blocks-panel')).toBeVisible();

  await page.locator('#btn-add-block').click();
  await expect(page.locator('#block-modal')).toBeVisible();
  await page.fill('#block-start', '2025-01-01T00:00');
  await page.fill('#block-end', '2025-01-01T00:10');

  const [postReq, postRes] = await Promise.all([
    page.waitForRequest(r => r.url().endsWith('/api/blocks') && r.method() === 'POST'),
    page.waitForResponse(r => r.url().endsWith('/api/blocks') && r.request().method() === 'POST'),
    page.locator('#block-form button[type=submit]').click(),
  ]);
  expect(postReq.method()).toBe('POST');
  expect(postRes.ok()).toBeTruthy();

  const created = await postRes.json();
  const createdId = created.id;
  const slot0 = page.locator('[data-slot-index="0"]');
  await expect(slot0).toHaveClass(/grid-slot--blocked/);

  const item = page.locator(`[data-block-id="${createdId}"]`);
  await expect(item).toHaveCount(1);

  // ---- delete block ----
  page.once('dialog', d => d.accept());
  const [delReq, delRes] = await Promise.all([
    page.waitForRequest(r => r.url().includes(`/api/blocks/${createdId}`) && r.method() === 'DELETE'),
    page.waitForResponse(r => r.url().includes(`/api/blocks/${createdId}`) && r.request().method() === 'DELETE'),
    item.locator('.delete-block').click(),
  ]);
  expect(delReq.method()).toBe('DELETE');
  expect(delRes.ok()).toBeTruthy();
  await expect(slot0).not.toHaveClass(/grid-slot--blocked/);

  // ---- import from Sheets ----
  page.once('dialog', d => d.accept());
  const [getImpReq, postImpReq, getImpRes, postImpRes] = await Promise.all([
    page.waitForRequest(r => r.url().includes('/api/blocks/import') && r.method() === 'GET'),
    page.waitForRequest(r => r.url().includes('/api/blocks/import') && r.method() === 'POST'),
    page.waitForResponse(r => r.url().includes('/api/blocks/import') && r.request().method() === 'GET'),
    page.waitForResponse(r => r.url().includes('/api/blocks/import') && r.request().method() === 'POST'),
    page.locator('#btn-import-blocks').click(),
  ]);
  expect(getImpReq.method()).toBe('GET');
  expect(getImpRes.ok()).toBeTruthy();
  expect(postImpReq.method()).toBe('POST');
  expect(postImpRes.ok()).toBeTruthy();

  await expect(slot0).toHaveClass(/grid-slot--blocked/);
});
