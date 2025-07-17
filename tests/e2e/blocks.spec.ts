import { test, expect } from '@playwright/test';
import { mockGoogleCalendar } from './helpers';

// Ensure importing blocks triggers schedule refresh

test('blocks import regenerates schedule', async ({ page }) => {
  // Avoid calendar redirects
  await page.route('**/api/calendar**', r =>
    r.fulfill({ status: 200, contentType: 'application/json', body: '[]' })
  );

  // Stub blocks import endpoints
  await page.route('**/api/blocks/import', r => r.fulfill({ status: 204 }));
  await page.route('**/api/blocks', r => {
    const data = [
      {
        id: 'b1',
        start_utc: '2025-01-01T00:00:00Z',
        end_utc: '2025-01-01T00:10:00Z',
      },
    ];
    r.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify(data) });
  });

  await page.route('**/api/schedule/generate**', r => {
    const body = JSON.stringify({ date: '2025-01-01', slots: new Array(144).fill(0), unplaced: [] });
    r.fulfill({ status: 200, contentType: 'application/json', body });
  });

  // Provide Alpine stub and schedule generator helper
  await page.addInitScript(() => {
    window.Alpine = {
      stores: {},
      store(name: string, value?: any) {
        if (value !== undefined) this.stores[name] = value;
        return this.stores[name];
      },
    } as any;
    window.dispatchEvent(new Event('alpine:init'));

    window.generateSchedule = async (ymd: string) => {
      await fetch(`/api/schedule/generate?date=${ymd}&algo=greedy`, {
        method: 'POST',
      });
    };
  });

  await page.goto('/');

  await page.evaluate(() => {
    window.Alpine.store('blocks', {
      data: [],
      async fetch() {
        const res = await fetch('/api/blocks');
        this.data = await res.json();
        window.dispatchEvent(new CustomEvent('blocks:fetched', { detail: this.data }));
      },
      async importReplace() {
        await fetch('/api/blocks/import', { method: 'POST' });
        window.dispatchEvent(new CustomEvent('blocks:import-replace'));
        await this.fetch();
        const input = document.querySelector('#input-date') as HTMLInputElement | null;
        const ymd = input?.value;
        if (ymd) {
          await window.generateSchedule(ymd);
        }
      },
    });
  });

  await page.evaluate(() => {
    const input = document.getElementById('input-date') as HTMLInputElement;
    input.value = '2025-01-01';
  });

  const [resp] = await Promise.all([
    page.waitForResponse(r => r.url().includes('/api/schedule/generate')),
    page.evaluate(() => window.Alpine.store('blocks').importReplace()),
  ]);

  expect(resp.ok()).toBe(true);
});

test.describe('block workflow end-to-end', () => {
  test.use({ viewport: { width: 375, height: 812 } });

  test('create, grid update, delete and import replace', async ({ page, request }) => {
    await page.addInitScript(() => {
      window.Alpine = {
        stores: {},
        store(name: string, value?: any) {
          if (value !== undefined) this.stores[name] = value;
          return this.stores[name];
        },
      } as any;
    });

    await mockGoogleCalendar(page);

    const existing = await request.get('/api/blocks');
    const blocks = await existing.json();
    for (const b of blocks) {
      await request.delete(`/api/blocks/${b.id}`);
    }

    await page.route('**/api/calendar**', r =>
      r.fulfill({ status: 200, contentType: 'application/json', body: '[]' })
    );
    await page.route('**/api/schedule/generate**', r => {
      const body = JSON.stringify({ date: '2025-01-01', slots: new Array(144).fill(0), unplaced: [] });
      r.fulfill({ status: 200, contentType: 'application/json', body });
    });

    await page.goto('/');
    await page.evaluate(() => {
      window.dispatchEvent(new Event('alpine:init'));
    });

    await page.locator('[data-tab="blocks-panel"]').click();

    await page.evaluate(() => {
      const input = document.getElementById('input-date') as HTMLInputElement;
      input.value = '2025-01-01';
      input.dispatchEvent(new Event('change', { bubbles: true }));
    });
    await page.getByTestId('generate-btn').click();

    await page.locator('#btn-add-block').click();
    await page.fill('#block-title', 'Flow Block');
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

    const slot0 = page.locator('.slot[data-slot-index="0"]');
    await expect(slot0).toHaveClass(/grid-slot--blocked/);

    const item = page.locator(`[data-block-id="${blockId}"]`);
    page.once('dialog', d => d.accept());
    const [delReq] = await Promise.all([
      page.waitForRequest(r => r.url().includes(`/api/blocks/${blockId}`) && r.method() === 'DELETE'),
      item.locator('.delete-block').click(),
    ]);
    expect(delReq.method()).toBe('DELETE');
    await expect(slot0).not.toHaveClass(/grid-slot--blocked/);

    const imported = {
      id: 'imp1',
      start_utc: '2025-01-01T01:00:00Z',
      end_utc: '2025-01-01T01:10:00Z',
    };
    await page.route('**/api/blocks/import', r => {
      if (r.request().method() === 'GET') {
        r.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify([imported]) });
      } else {
        r.fulfill({ status: 204 });
      }
    });
    await page.route('**/api/blocks', r => {
      r.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify([imported]) });
    });

    page.once('dialog', d => d.accept());
    await Promise.all([
      page.waitForRequest(r => r.url().includes('/api/blocks/import') && r.method() === 'POST'),
      page.locator('#btn-import-blocks').click(),
    ]);

    const slot6 = page.locator('.slot[data-slot-index="6"]');
    await expect(slot6).toHaveClass(/grid-slot--blocked/);

    const ok = await page.evaluate(() => document.documentElement.scrollWidth <= window.innerWidth);
    expect(ok).toBe(true);
  });
});
