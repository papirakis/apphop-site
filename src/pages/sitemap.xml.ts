import { APPS } from '../data/apps';
const paths = ['', 'apps/', 'press/', 'about/', 'contact/', 'privacy/', 'legal/', ...APPS.flatMap((a) => [`apps/${a.slug}/`, `apps/${a.slug}/support/`, `apps/${a.slug}/privacy/`])];
export const GET = () => new Response(
  `<?xml version="1.0" encoding="UTF-8"?>\n<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n${paths.map((p) => `  <url><loc>https://www.apphop.app/${p}</loc></url>`).join('\n')}\n</urlset>\n`,
  { headers: { 'Content-Type': 'application/xml' } });
