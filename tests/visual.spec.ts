import { test, expect } from '@playwright/test';
import { PAGES } from './pages';

// Full-page visual regression: 9 templates x 8 viewports x light/dark = 144 baselines.
test.beforeEach(({}, info) => { test.skip(info.project.name === 'narrow-320', 'layout-only project'); });

for (const scheme of ['light', 'dark'] as const) {
  for (const p of PAGES) {
    test(`${p.name} ${scheme}`, async ({ page }) => {
      await page.emulateMedia({ colorScheme: scheme, reducedMotion: 'reduce' });
      await page.goto(p.path, { waitUntil: 'networkidle' });
      await page.evaluate(() => document.fonts.ready);
      await expect(page).toHaveScreenshot(`${p.name}-${scheme}.png`, { fullPage: true, mask: [page.locator('.site-footer p.muted').last()] });
    });
  }
}
