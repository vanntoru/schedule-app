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
