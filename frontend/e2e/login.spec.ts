import { expect, test } from '@playwright/test';

test('login is responsive, keyboard accessible and has a working password toggle', async ({ page }) => {
  await page.goto('/auth/login/');
  await expect(page.getByRole('heading', { name: 'Вход в кабинет', exact: true })).toBeVisible();
  await expect(page.getByText('Все данные вымышленные.', { exact: false })).toBeVisible();
  await page.screenshot({ path: `test-results/login-${test.info().project.name}.png`, fullPage: true });
  const password = page.getByLabel('Пароль', { exact: true });
  await password.fill('synthetic-toggle-only');
  const toggle = page.getByRole('button', { name: 'Показать пароль' });
  await toggle.focus();
  await page.keyboard.press('Space');
  await expect(password).toHaveAttribute('type', 'text');
  await expect(toggle).toHaveAttribute('aria-pressed', 'true');
  await expect(password).toHaveValue('synthetic-toggle-only');
  await page.getByRole('button', { name: 'Скрыть пароль' }).click();
  await expect(password).toHaveAttribute('type', 'password');
  await page.getByRole('link', { name: 'Забыли пароль?' }).click();
  await expect(page.getByRole('heading', { name: 'Нужна помощь со входом?' })).toBeInViewport();
  expect(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth)).toBe(true);
});

test('failed login announces errors and keeps the form usable', async ({ page }) => {
  await page.goto('/auth/login/');
  await page.getByLabel('Логин', { exact: true }).fill('synthetic_invalid_ui');
  await page.getByLabel('Пароль', { exact: true }).fill('wrong-ui-only');
  await page.getByRole('checkbox', { name: 'Запомнить меня' }).check();
  await page.getByRole('button', { name: 'Войти', exact: true }).click();
  await expect(page.getByRole('alert')).toContainText('Не удалось войти');
  await expect(page.getByRole('alert')).toBeFocused();
  await expect(page.getByLabel('Логин', { exact: true })).toHaveValue('synthetic_invalid_ui');
  await expect(page.getByLabel('Пароль', { exact: true })).toHaveValue('');
  await expect(page.getByRole('checkbox', { name: 'Запомнить меня' })).toBeChecked();
  await expect(page.getByRole('button', { name: 'Войти', exact: true })).toBeEnabled();
  await page.screenshot({ path: `test-results/login-error-${test.info().project.name}.png`, fullPage: true });
});

test('native login still works with JavaScript disabled', async ({ browser, baseURL }) => {
  const context = await browser.newContext({ baseURL, javaScriptEnabled: false });
  try {
    const page = await context.newPage();
    await page.goto('/auth/login/?next=/profile');
    await expect(page.getByRole('button', { name: 'Показать пароль' })).toBeHidden();
    await page.getByLabel('Логин', { exact: true }).fill('browser_student');
    await page.getByLabel('Пароль', { exact: true }).fill('ephemeral-browser-test-only');
    await page.getByRole('button', { name: 'Войти', exact: true }).click();
    await expect(page).toHaveURL('/profile');
    expect((await (await context.request.get('/api/v1/me/')).json()).username).toBe('browser_student');
  } finally {
    await context.close();
  }
});
