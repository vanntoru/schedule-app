import { type Page } from '@playwright/test';

/**
 * Pseudo login for Playwright tests.
 *
 * Skips the Google OAuth flow by inserting a dummy token into
 * ``sessionStorage`` before any page scripts run.
 *
 * @param page   Playwright page instance
 * @param token  Token value to store (defaults to 'test-token')
 */
export async function pseudoLogin(page: Page, token: string = 'test-token'): Promise<void> {
  await page.addInitScript((value: string) => {
    window.sessionStorage.setItem('token', value);
  }, token);
}

/**
 * Mock Google Calendar API requests during Playwright tests.
 *
 * Intercepts network calls to ``/api/calendar`` and returns ``events``
 * without contacting the real Google API.
 *
 * @param page    Playwright page instance
 * @param events  Array of event objects to return (defaults to empty array)
 */
export async function mockGoogleCalendar(
  page: Page,
  events: any[] = [],
): Promise<void> {
  await page.route('**/api/calendar**', route => {
    route.fulfill({
      status: 200,
      contentType: 'application/json',
      body: JSON.stringify(events),
    });
  });
}
