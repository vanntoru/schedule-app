import { test, expect } from '@playwright/test';
import { mockGoogleCalendar } from './helpers';

test('clear cache button loads new tasks', async ({ page }) => {
  await mockGoogleCalendar(page);

  const taskLists = [
    [{
      id: 't1',
      title: 'Task A',
      category: '',
      duration_min: 10,
      duration_raw_min: 10,
      priority: 'A'
    }],
    [{
      id: 't2',
      title: 'Task B',
      category: '',
      duration_min: 20,
      duration_raw_min: 20,
      priority: 'A'
    }]
  ];
  let importCount = 0;
  let currentTasks: any[] = [];

  await page.route('**/api/tasks/import', route => {
    currentTasks = taskLists[Math.min(importCount, taskLists.length - 1)];
    importCount++;
    route.fulfill({
      status: 200,
      contentType: 'application/json',
      body: JSON.stringify(currentTasks)
    });
  });

  await page.route('**/api/tasks', route => {
    route.fulfill({
      status: 200,
      contentType: 'application/json',
      body: JSON.stringify(currentTasks)
    });
  });

  await page.goto('/');

  await expect(page.locator('.task-card')).toHaveCount(0);

  await page.locator('#btn-import-sheets').click();
  await expect(page.locator('.task-card')).toHaveCount(1);
  await expect(page.locator('.task-card')).toContainText('Task A');

  const [delReq] = await Promise.all([
    page.waitForRequest(r => r.url().includes('/api/tasks/cache') && r.method() === 'DELETE'),
    page.locator('#btn-clear-cache').click(),
  ]);
  expect(delReq.method()).toBe('DELETE');

  const toast = page.locator('.schedule-toast');
  await expect(toast).toHaveCount(1);
  await expect(toast).toContainText('Cache cleared');

  await page.locator('#btn-import-sheets').click();
  await expect(page.locator('.task-card')).toHaveCount(1);
  await expect(page.locator('.task-card')).toContainText('Task B');
});
