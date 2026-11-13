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
  await expect(page).toHaveURL('/auth/login/');
  await expect(page.getByRole('heading', { name: 'Вход в кабинет', exact: true })).toBeVisible();
  await expect(page.getByText('С возвращением', { exact: false })).toBeVisible();
  await expect(page.getByRole('button', { name: 'Показать пароль' })).toBeVisible();
  expect((await page.request.get('/api/v1/me/')).status()).toBe(403);
  await page.screenshot({ path: `test-results/after-logout-${test.info().project.name}.png`, fullPage: true });
  await page.goto('/profile');
  await expect(page.getByRole('link', { name: 'Войти в кабинет' })).toBeVisible();
  await page.getByRole('link', { name: 'Войти в кабинет' }).click();
  await page.getByLabel('Логин', { exact: true }).fill('browser_student');
  await page.getByLabel('Пароль', { exact: true }).fill('ephemeral-browser-test-only');
  await page.getByRole('button', { name: 'Войти', exact: true }).click();
  await expect(page.getByRole('heading', { name: 'Демонстрационный студент' })).toBeVisible();
});

test('two student sessions remain isolated and cannot assign privileges', async ({ browser, baseURL, viewport, userAgent, isMobile, hasTouch, deviceScaleFactor }) => {
  const options = { baseURL, viewport, userAgent, isMobile, hasTouch, deviceScaleFactor };
  const first = await browser.newContext(options);
  const second = await browser.newContext(options);
  try {
    for (const [context, username] of [
      [first, 'browser_student'], [second, 'browser_student_other'],
    ] as const) {
      const page = await context.newPage();
      await page.goto('/auth/login/');
      await page.locator('[name=username]').fill(username);
      await page.locator('[name=password]').fill('ephemeral-browser-test-only');
      await page.getByRole('button', { name: 'Войти', exact: true }).click();
      await expect(page).toHaveURL('/profile');
    }
    const firstProfile = await (await first.request.get('/api/v1/me/')).json();
    const secondProfile = await (await second.request.get('/api/v1/me/')).json();
    expect(firstProfile.id).not.toBe(secondProfile.id);
    expect(firstProfile.student_profile.group).toBe('ДЕМО-1');
    expect(secondProfile.student_profile.group).toBe('ДЕМО-2');
    const forged = await first.request.get(`/api/v1/me/?user_id=${secondProfile.id}`);
    expect((await forged.json()).id).toBe(firstProfile.id);
    const csrf = await (await first.request.get('/api/v1/csrf/')).json();
    const update = await first.request.patch('/api/v1/me/', {
      headers: { 'X-CSRFToken': csrf.csrfToken },
      data: { id: secondProfile.id, roles: ['deanery_staff'], is_superuser: true },
    });
    expect(update.status()).toBe(405);
    expect((await (await first.request.get('/api/v1/me/')).json()).roles).toEqual(['student']);
  } finally {
    await first.close();
    await second.close();
  }
});
