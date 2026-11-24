# apphop-site

Public marketing site for the AppHop app portfolio: a static [Astro](https://astro.build) site, mobile-first,
built once and published to three CDNs (CloudFront primary, Fastly and Bunny standby) with DNS steering.

- **Staging:** https://papirakis.github.io/apphop-site/ (GitHub Pages, `noindex`, deployed on every push to `main`)
- **Production (planned):** https://www.apphop.app/ — apex `apphop.app` 301-redirects to `www`

## Layout

| Path | What |
| --- | --- |
| `src/data/apps.ts` | One entry per app → overview, support and privacy pages (App Store Connect URLs) |
| `src/data/site.ts` | Site name, nav, role contact addresses |
| `src/styles/tokens.css` | **Design tokens — the only file the brand needs to replace** (colors, type, spacing, radii) |
| `src/styles/global.css` | Mobile-first layout; breakpoints 600 / 900 / 1280 / 1600 px |
| `src/layouts/Base.astro` | Header (inline nav ≥900 px, full-height sheet menu below), footer, SEO meta |
| `tests/` | Playwright: 8-viewport visual regression, mobile checks, axe |
| `lighthouserc.json` | Lighthouse CI mobile budgets (LCP < 2.0 s, CLS < 0.05, TBT < 150 ms, ≤ 500 KB, JS ≤ 50 KB) |
| `cdn/cloudfront/` | CloudFormation: private S3 origin (OAC) + CloudFront; us-east-1 replica bucket |
| `cdn/fastly/` | Terraform: Fastly VCL service (apex redirect, headers, S3 replica origin, log streaming) |
| `cdn/bunny/` | Idempotent Bunny API setup script (storage zone, pull zone, edge rules, cert upload) |
| `scripts/` | `publish.py` (all origins + purges), `parity_check.py` (cross-CDN), `manifest.py`, `acme_issue.sh` |

## Information architecture

```
/                         portfolio home
/apps/                    all apps
/apps/<slug>/             app overview (App Store badge, features, FAQ)
/apps/<slug>/support/     App Store "Support URL"
/apps/<slug>/privacy/     App Store "Privacy Policy URL"
/press/  /about/  /contact/  /privacy/  /legal/  /404.html
/healthz.json  /manifest.json  /sitemap.xml  /robots.txt
```

Header: Apps · Press · About · Contact. Per-app sub-nav: Overview · Support · Privacy. Breadcrumbs at depth 2–3.

## Develop

```bash
npm ci
npm run dev                 # http://localhost:4321
npm run build               # dist/ + dist/manifest.json
npx playwright install --with-deps chromium webkit
npm test                    # functional + a11y + visual (visual baselines come from CI's pinned container)
npm run lhci                # Lighthouse CI mobile budgets
npm run links               # internal link check
```

Visual baselines are generated in CI's pinned container (`mcr.microsoft.com/playwright:v1.65.1-noble`) by the
**Update visual baselines** workflow; review the artifact and commit `tests/__screenshots__/`.

## Brand handoff (marketing-lead)

Replace `src/styles/tokens.css`, `public/brand/*` (logo, favicon, OG image) and `public/apps/*.svg` (app icons),
and edit copy in `src/data/*.ts`. No template changes are needed. Expect visual baselines to change: run the
baseline workflow and approve the diff in the PR.

## Contact addresses

The site uses role addresses only (`hello@`, `support@`, `press@`, `privacy@` at apphop.app). They must exist
before production launch (mail routing is a separate, approval-gated DNS change).
