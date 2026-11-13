import { expect, test } from '@playwright/test';

test('student can sign in, read own profile, and sign out', async ({ page }) => {
  await page.goto('/profile');
  await page.getByRole('link', { name: 'Войти в кабинет' }).click();
  await page.locator('[name=username]').fill('browser_student');
  await page.locator('[name=password]').fill('ephemeral-browser-test-only');
  await page.getByRole('button', { name: 'Войти', exact: true }).click();
  await expect(page.getByRole('heading', { name: 'Демонстрационный студент' })).toBeVisible();
  await expect(page.getByText('ДЕМО-1', { exact: true })).toBeVisible();
  expect(await page.evaluate(() => document.documentElement.scrollWidth <= window.innerWidth)).toBe(true);
  await page.screenshot({ path: `test-results/profile-${test.info().project.name}.png`, fullPage: true });
  await page.getByRole('button', { name: 'Выйти', exact: true }).click();
  await expect(page).toHaveURL('/');
  await page.goto('/profile');
  await expect(page.getByRole('link', { name: 'Войти в кабинет' })).toBeVisible();
});
