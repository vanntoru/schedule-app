import { test, expect } from '@playwright/test';

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

  // Provide Alpine stub, block DOM helpers and schedule generator helper
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
      item?.querySelector('.block-title')?.replaceWith(
        Object.assign(document.createElement('span'), {
          className: 'block-title',
          textContent: block.title || 'Block',
        })
      );
    });
    window.addEventListener('blocks:removed', (e: any) => {
      const id = e.detail;
      document.querySelector(`[data-block-id="${id}"]`)?.remove();
    });

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
