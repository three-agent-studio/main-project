import { expect, test, type Page } from '@playwright/test';

async function login(page: Page, user: string, destination: string) {
  await page.goto('/auth/login/', { waitUntil: 'domcontentloaded' });
  await page.getByLabel('Логин', { exact: true }).fill(user);
  await page.getByLabel('Пароль', { exact: true }).fill('ephemeral-browser-test-only');
  await page.getByRole('button', { name: 'Войти', exact: true }).click();
  await expect(page).toHaveURL(destination);
}

test('student submits a request, staff answers, only its owner receives the reply', async ({
  page, browser, baseURL,
}, info) => {
  // The end-to-end flow spans three browsers' sessions on one CI runner.
  test.setTimeout(60000);
  const message = `Тестовая справка ${info.project.name} ${Date.now()}`;
  const answer = `Справка готова ${info.project.name} ${Date.now()}`;
  await login(page, 'browser_student', '/profile');
  const navigation = page.getByRole('navigation', {name: 'Основная навигация'});
  const openRequests = () => navigation.getByRole('link', {name: 'Заявки', exact: true}).click();
  const openNotices = () => navigation.getByRole('link', {name: /^(Уведомления|Новости)$/}).click();
  await openRequests();
  await page.getByLabel('Комментарий (необязательно)').fill(message);
  await page.getByRole('button', {name: 'Подать заявку'}).click();
  const studentTicket = page.getByRole('article').filter({hasText: message});
  await expect(studentTicket.getByText('Подана', {exact: true}).first()).toBeVisible();
  expect(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth)).toBe(true);

  const office = await browser.newContext({baseURL, viewport: page.viewportSize() ?? undefined});
  const employee = await office.newPage();
  try {
    await login(employee, 'browser_employee', '/deanery');
    const ticket = employee.getByRole('article').filter({hasText: message});
    await ticket.getByRole('button', {name: 'Взять в работу'}).click();
    await expect(ticket.getByRole('button', {name: 'Отметить готовой'})).toBeVisible();
    await ticket.getByLabel('Ответ студенту').fill(answer);
    await ticket.getByRole('button', {name: 'Отметить готовой'}).click();
    await expect(ticket.getByText('Готова', {exact: true}).first()).toBeVisible();
    expect(await employee.evaluate(() => document.documentElement.scrollWidth <= innerWidth)).toBe(true);
  } finally {
    await office.close();
  }

  // The student's tab has remained on /requests throughout both staff updates.
  await expect(studentTicket.getByText('Готова', {exact: true}).first()).toBeVisible({timeout: 15_000});
  await expect(studentTicket.getByRole('region', {name: 'Ответ деканата'}).getByText(answer)).toBeVisible();
  await studentTicket.getByText('История заявки (3)').click();
  await expect(studentTicket.getByRole('list', {name: 'История статусов'}).getByText(answer)).toBeVisible();
  await openNotices();
  const notice = page.getByRole('article').filter({hasText: answer});
  await expect(notice).toBeVisible();
  await notice.getByRole('button', {name: 'Отметить прочитанным'}).click();
  await expect(notice.getByText('Прочитано', {exact: true})).toBeVisible();
  // A fresh mount discards optimistic state and fetches the persisted receipt.
  await openRequests();
  await openNotices();
  await expect(notice.getByText('Прочитано', {exact: true})).toBeVisible();

  const other = await browser.newContext({baseURL});
  try {
    const student = await other.newPage();
    await login(student, 'browser_student_other', '/profile');
    await student.getByRole('link', {name: 'Заявки', exact: true}).click();
    await expect(student.getByText('Заявок пока нет')).toBeVisible();
    await student.getByRole('link', {name: /^(Уведомления|Новости)$/}).click();
    await expect(student.getByText('Уведомлений пока нет')).toBeVisible();
    await expect(student.getByText(answer)).toHaveCount(0);
  } finally {
    await other.close();
  }

  // Simulate expiry with the form already open, without submitting any new records.
  await openRequests();
  await expect(page.getByRole('button', {name: 'Подать заявку'})).toBeVisible();
  await expect(page.getByText(message, {exact: true})).toBeVisible();
  await page.context().clearCookies({name: 'sessionid'});
  await page.getByRole('button', {name: 'Подать заявку'}).click();
  await expect(page).toHaveURL(/\/auth\/login\/\?next=%2Frequests$/);
});
