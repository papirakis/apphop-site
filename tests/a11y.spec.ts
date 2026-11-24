import { test, expect } from '@playwright/test';
import AxeBuilder from '@axe-core/playwright';
import { PAGES } from './pages';

// axe on every template at a phone width and a desktop width: zero serious/critical WCAG 2.2 AA violations.
test.skip(({}, info) => !['iphone-15', 'pixel-7', 'desktop'].includes(info.project.name), 'a11y runs on phone + desktop projects');

for (const scheme of ['light', 'dark'] as const) {
  for (const p of PAGES) {
    test(`axe ${p.name} ${scheme}`, async ({ page }) => {
      await page.emulateMedia({ colorScheme: scheme });
      await page.goto(p.path);
      const results = await new AxeBuilder({ page }).withTags(['wcag2a', 'wcag2aa', 'wcag21a', 'wcag21aa', 'wcag22aa']).analyze();
      const bad = results.violations.filter((v) => v.impact === 'serious' || v.impact === 'critical');
      expect(bad.map((v) => `${v.id}: ${v.nodes.map((n) => n.target.join(' ')).join(', ')}`)).toEqual([]);
    });
  }
}
