import { test, expect } from '@playwright/test';
import { ALL_PATHS } from './pages';

const isPhoneOrTablet = (w: number) => w < 900;

test.describe('layout', () => {
  for (const path of ALL_PATHS) {
    test(`no horizontal scroll: /${path}`, async ({ page }) => {
      await page.goto(path);
      const { sw, vw } = await page.evaluate(() => ({ sw: document.documentElement.scrollWidth, vw: window.innerWidth }));
      expect(sw).toBeLessThanOrEqual(vw);
    });
  }
});

test('tap targets in navigation and controls are at least 44px', async ({ page }) => {
  for (const path of ['', 'apps/roommeasure/', 'contact/']) {
    await page.goto(path);
    const small = await page.evaluate(() => {
      const sel = '.site-header a, .site-header summary, .subnav a, .crumbs a, .site-footer a, .btn, .store-badge, details.faq summary, .app-card .more';
      return [...document.querySelectorAll<HTMLElement>(sel)]
        .filter((el) => el.offsetParent !== null)
        .map((el) => ({ t: (el.textContent || '').trim().slice(0, 30), r: el.getBoundingClientRect() }))
        .filter(({ r }) => r.height < 44 - 0.5 || r.width < 24)
        .map(({ t, r }) => `${t} ${Math.round(r.width)}x${Math.round(r.height)}`);
    });
    expect(small, `on /${path}`).toEqual([]);
  }
});

test('mobile menu opens, focuses first link, closes on Escape', async ({ page }, info) => {
  const w = page.viewportSize()!.width;
  await page.goto('');
  if (!isPhoneOrTablet(w)) {
    await expect(page.locator('.nav-inline')).toBeVisible();
    await expect(page.locator('.menu > summary')).toBeHidden();
    return;
  }
  await expect(page.locator('.nav-inline')).toBeHidden();
  await page.locator('.menu > summary').click();
  await expect(page.locator('.menu-sheet')).toBeVisible();
  await expect(page.locator('.menu-sheet a').first()).toBeFocused();
  await page.keyboard.press('Escape');
  await expect(page.locator('.menu-sheet')).toBeHidden();
  info.annotations.push({ type: 'width', description: String(w) });
});

test('app page has subnav, store badge and links to support + privacy', async ({ page }) => {
  await page.goto('apps/tendril/');
  await expect(page.locator('.subnav a[aria-current="page"]')).toHaveText('Overview');
  await expect(page.locator('.store-badge')).toBeVisible();
  for (const sub of ['support', 'privacy']) {
    const r = await page.request.get(`apps/tendril/${sub}/`);
    expect(r.status()).toBe(200);
  }
});

test('safe-area: viewport-fit=cover and header respects inset', async ({ page }) => {
  await page.goto('');
  await expect(page.locator('meta[name="viewport"]')).toHaveAttribute('content', /viewport-fit=cover/);
  const pt = await page.evaluate(() => getComputedStyle(document.querySelector('.site-header')!).paddingTop);
  expect(pt).toBeDefined();
});

test('healthz.json returns build id', async ({ request }) => {
  const r = await request.get('healthz.json');
  expect(r.ok()).toBeTruthy();
  expect((await r.json()).build_id).toBeTruthy();
});
