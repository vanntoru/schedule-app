import { test, expect } from '@playwright/test';
import { mockGoogleCalendar } from './helpers';

// Task CRUD scenario: create, update and delete via UI

test('task CRUD via modal form', async ({ page, request }) => {
  // Stub calendar API to avoid 401 redirect
  await mockGoogleCalendar(page);

  // Remove any existing tasks
  const existing = await request.get('/api/tasks');
  const items = await existing.json();
  for (const t of items) {
    await request.delete(`/api/tasks/${t.id}`);
  }

  await page.goto('/');

  // ---- Create a new task ----
  await page.locator('#btn-add-task').click();
  await page.fill('#task-title', 'E2E Task');
  await page.fill('#task-category', 'e2e');
  await page.fill('#task-duration', '10');
  await page.selectOption('#task-priority', 'A');

  const [postReq] = await Promise.all([
    page.waitForRequest(r => r.url().endsWith('/api/tasks') && r.method() === 'POST'),
    page.locator('#task-form button[type=submit]').click(),
  ]);
  expect(postReq.method()).toBe('POST');

  const card = page.locator('.task-card').filter({ hasText: 'E2E Task' });
  await expect(card).toBeVisible();

  const taskId = await card.getAttribute('data-task-id');
  expect(taskId).toBeTruthy();

  // ---- Update the task ----
  await card.locator('.edit-task').click();
  await page.fill('#task-title', 'Updated Task');

  const [putReq] = await Promise.all([
    page.waitForRequest(r => r.url().includes(`/api/tasks/${taskId}`) && r.method() === 'PUT'),
    page.locator('#task-form button[type=submit]').click(),
  ]);
  expect(putReq.method()).toBe('PUT');
  const updated = page.locator(`[data-task-id="${taskId}"]`);
  await expect(updated).toContainText('Updated Task');

  // ---- Delete the task ----
  page.once('dialog', d => d.accept());
  const [delReq] = await Promise.all([
    page.waitForRequest(r => r.url().includes(`/api/tasks/${taskId}`) && r.method() === 'DELETE'),
    updated.locator('.delete-task').click(),
  ]);
  expect(delReq.method()).toBe('DELETE');
  await expect(page.locator(`[data-task-id="${taskId}"]`)).toHaveCount(0);
});

