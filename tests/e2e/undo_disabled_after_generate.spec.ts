import { test, expect } from '@playwright/test';

const sampleSchedule = {
  date: '2025-01-01',
  slots: new Array(144).fill(0),
  unplaced: [],
};

test('undo/redo disabled after generate', async ({ page }) => {
  await page.route('**/api/calendar**', r =>
    r.fulfill({ status: 200, contentType: 'application/json', body: '[]' })
  );
  await page.route('**/api/schedule/generate**', r =>
    r.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify(sampleSchedule) })
  );

  await page.goto('http://localhost:5173');
  await page.getByTestId('generate-btn').click();

  await expect(page.locator('#undo-btn')).toBeDisabled();
  await expect(page.locator('#redo-btn')).toBeDisabled();
});
