import { expect, test } from '@playwright/test';

test('teacher assigns homework, records debt and closes it; students see personal results', async ({
  page, browser, baseURL, viewport, userAgent, isMobile, hasTouch, deviceScaleFactor,
}) => {
  test.setTimeout(90_000);
  const title = `ДЗ ${test.info().project.name}`;
  const credit = `Зачёт ${test.info().project.name}`;
  await page.goto('/auth/login/');
  await page.getByLabel('Логин', {exact:true}).fill('browser_teacher');
  await page.getByLabel('Пароль', {exact:true}).fill('ephemeral-browser-test-only');
  await page.getByRole('button', {name:'Войти',exact:true}).click();
  await expect(page).toHaveURL('/teaching');
  await expect(page.getByRole('heading', {name:'Кабинет преподавателя',exact:true})).toBeVisible();
  await page.getByLabel('Дисциплина и группа').selectOption({label:'Демо: базы данных — ДЕМО-1'});
  await page.getByLabel('Название', {exact:true}).fill(title);
  await page.getByLabel('Задание или описание').fill('Вымышленное задание: подготовить проект.');
  await page.getByLabel('Срок сдачи', {exact:true}).fill('2026-12-01T18:00');
  await page.getByRole('button', {name:'Создать работу',exact:true}).click();
  const row = page.getByRole('form', {name:'Результат: Демонстрационный студент',exact:true});
  await expect(row).toBeVisible();
  await row.getByLabel('Результат', {exact:true}).selectOption('debt');
  await row.getByLabel('Комментарий', {exact:true}).fill(`Демо-задолженность ${test.info().project.name}`);
  const [debtResponse] = await Promise.all([
    page.waitForResponse(r => r.url().endsWith('/results/') && r.request().method() === 'POST'),
    row.getByRole('button', {name:'Сохранить результат',exact:true}).click(),
  ]);
  expect(debtResponse.status()).toBe(201);
  await expect(row.getByRole('status')).toHaveText('Результат сохранён');
  expect(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth)).toBe(true);

  const student = await browser.newContext({baseURL, viewport, userAgent, isMobile, hasTouch, deviceScaleFactor});
  try {
    const learner = await student.newPage();
    await learner.goto('/auth/login/');
    await learner.getByLabel('Логин', {exact:true}).fill('browser_student');
    await learner.getByLabel('Пароль', {exact:true}).fill('ephemeral-browser-test-only');
    await learner.getByRole('button', {name:'Войти',exact:true}).click();
    await expect(learner).toHaveURL('/profile');
    await learner.goto('/academics');
    const card = learner.getByRole('article').filter({has:learner.getByRole('heading', {name:`Демо: базы данных: ${title}`,exact:true})});
    await expect(card.getByText('Задолженность', {exact:true})).toBeVisible();
    await learner.getByRole('checkbox', {name:'Только задолженности'}).check();
    await expect(card).toBeVisible();

    await row.getByLabel('Результат', {exact:true}).selectOption('passed');
    const [passedResponse] = await Promise.all([
      page.waitForResponse(r => r.url().endsWith('/results/') && r.request().method() === 'POST'),
      row.getByRole('button', {name:'Сохранить результат',exact:true}).click(),
    ]);
    expect(passedResponse.status()).toBe(200);
    await learner.reload();
    await expect(card.getByText('Зачтено', {exact:true})).toBeVisible();
    await learner.getByRole('checkbox', {name:'Только задолженности'}).check();
    await expect(card).toHaveCount(0);

    await page.getByLabel('Дисциплина и группа').selectOption({label:'Демо: базы данных — ДЕМО-1'});
    await page.getByLabel('Вид работы').selectOption('credit');
    await page.getByLabel('Название', {exact:true}).fill(credit);
    await page.getByLabel('Дата и время начала', {exact:true}).fill('2026-12-05T10:00');
    await page.getByRole('button', {name:'Создать работу',exact:true}).click();
    await expect(page.getByRole('heading', {name:credit,exact:true})).toBeVisible();
    await page.getByRole('button', {name:`Изменить: ${credit}`,exact:true}).click();
    await page.getByLabel('Дата и время начала', {exact:true}).fill('2026-12-06T12:00');
    const [dateResponse] = await Promise.all([
      page.waitForResponse(r => r.request().method() === 'PATCH'),
      page.getByRole('button', {name:'Сохранить изменения',exact:true}).click(),
    ]);
    expect(dateResponse.status()).toBe(200);
    await learner.reload();
    const scheduled = learner.getByRole('article').filter({has:learner.getByRole('heading', {name:credit,exact:true})});
    await expect(scheduled.getByText(/6 декабря 2026/)).toBeVisible();
    expect(await learner.evaluate(() => document.documentElement.scrollWidth <= innerWidth)).toBe(true);
    await learner.screenshot({path:`test-results/student-academics-${test.info().project.name}.png`,fullPage:true});
    await page.screenshot({path:`test-results/teacher-${test.info().project.name}.png`,fullPage:true});
    await learner.goto('/teaching');
    await expect(learner.getByRole('heading', {name:'Нужна роль преподавателя',exact:true})).toBeVisible();
  } finally {
    await student.close();
  }
});
