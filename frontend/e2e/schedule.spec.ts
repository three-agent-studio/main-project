import { expect, test } from '@playwright/test';

// A device far from Moscow must still see Moscow dates and class times.
test.use({timezoneId:'America/Los_Angeles'});

test('weekly schedule has seven day blocks, Moscow times and full teacher names', async ({page}) => {
  await page.goto('/auth/login/');
  await page.getByLabel('Логин', {exact:true}).fill('browser_student');
  await page.getByLabel('Пароль', {exact:true}).fill('ephemeral-browser-test-only');
  await page.getByRole('button', {name:'Войти',exact:true}).click();
  await expect(page).toHaveURL('/profile');
  await page.getByRole('link', {name:'Учёба',exact:true}).click();
  const weekdays = ['Понедельник','Вторник','Среда','Четверг','Пятница','Суббота','Воскресенье'];
  for (const name of weekdays) await expect(page.getByRole('region', {name,exact:true})).toBeVisible();
  const monday = page.getByRole('region', {name:'Понедельник',exact:true});
  await expect(monday.getByRole('heading', {name:'Высшая математика',exact:true})).toBeVisible();
  expect(await monday.locator('time').allTextContents()).toEqual(['08:00','10:00','12:00']);
  await expect(monday.getByText('Лебедев Артём Сергеевич')).toBeVisible();
  await expect(monday.getByText('ДЕМО-А · 201')).toBeVisible();
  await expect(page.getByText('Московское время · МСК', {exact:true})).toBeVisible();
  await expect(page.getByRole('region', {name:'Воскресенье',exact:true}).getByText('Занятий нет — свободный день')).toBeVisible();
  const today = page.getByRole('button', { name: 'Только сегодня' });
  await today.click();
  await expect(today).toHaveAttribute('aria-pressed', 'true');
  await expect(page.getByRole('region', {name: new RegExp(`^(${weekdays.join('|')})$`)})).toHaveCount(1);
  await today.click();
  await expect(page.getByRole('region', {name: 'Воскресенье', exact:true})).toBeVisible();
  expect(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth)).toBe(true);
  await page.screenshot({path:`test-results/schedule-days-${test.info().project.name}.png`,fullPage:true});
});
