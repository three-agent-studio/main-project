import { expect, test } from '@playwright/test';

test('welcome and navigation remain usable at the configured viewport', async ({ page }, info) => {
  await page.goto('/', { waitUntil: 'domcontentloaded' });
  const welcome = page.getByRole('region', { name: 'Учёба под рукой' });
  await expect(welcome.getByRole('link', { name: 'Войти в кабинет' })).toBeVisible();
  const widths = await page.evaluate(() => ({
    viewport: innerWidth,
    document: document.documentElement.scrollWidth,
    main: document.querySelector('main')?.scrollWidth,
    mainBox: document.querySelector('main')?.clientWidth,
  }));
  expect(widths.document).toBeLessThanOrEqual(widths.viewport);
  expect(widths.main).toBeLessThanOrEqual(widths.mainBox ?? 0);
  await page.screenshot({ path: `test-results/welcome-${info.project.name}.png`, fullPage: true, timeout: 10000 });
  await welcome.getByRole('link', { name: 'Войти в кабинет' }).click();
  await expect(page.getByRole('heading', { name: 'Вход в кабинет' })).toBeVisible();
});
