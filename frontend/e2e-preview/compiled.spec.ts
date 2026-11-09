import { expect, test } from '@playwright/test';

test('compiled UI boots through Gunicorn and serves real JavaScript', async ({ page }) => {
  const errors: string[] = [];
  page.on('pageerror', error => errors.push(error.message));
  page.on('requestfailed', request => errors.push(`${new URL(request.url()).pathname}: ${request.failure()?.errorText}`));

  await page.goto('/');
  await expect(page.getByRole('heading', { name: 'Ваш цифровой деканат', exact: true })).toBeVisible();
  const modulePath = await page.locator('script[type="module"]').getAttribute('src');
  expect(modulePath).toMatch(/^\/assets\/.+\.js$/);
  const bundle = await page.request.get(modulePath!);
  expect(bundle.status()).toBe(200);
  expect(bundle.headers()['content-type']).toContain('javascript');
  expect(bundle.headers()['content-encoding']).toBe('gzip');
  expect((await bundle.body()).length).toBeGreaterThan(0);

  await page.getByRole('link', { name: 'Мой профиль', exact: true }).click();
  await expect(page.getByRole('heading', { name: 'Мой профиль', exact: true })).toBeVisible();
  await expect(page.getByRole('link', { name: 'Войти в кабинет', exact: true })).toBeVisible();
  await page.reload(); // SPA fallback must also work on a direct nested URL.
  await expect(page.getByRole('heading', { name: 'Мой профиль', exact: true })).toBeVisible();
  expect(errors).toEqual([]);
});
