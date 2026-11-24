// @ts-check
import { defineConfig } from 'astro/config';

// SITE_URL / SITE_BASE let the same build target GitHub Pages staging
// (https://papirakis.github.io/apphop-site/) and production (https://www.apphop.app/).
const site = process.env.SITE_URL || 'https://www.apphop.app';
const base = process.env.SITE_BASE || '/';

export default defineConfig({
  site,
  base,
  trailingSlash: 'always',
  build: { format: 'directory', inlineStylesheets: 'always' },
  compressHTML: true,
});
