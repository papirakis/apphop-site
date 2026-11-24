// Base-aware URL helper so the same build works under /apphop-site/ (staging) and / (production).
export function u(path = ''): string {
  const base = import.meta.env.BASE_URL.endsWith('/') ? import.meta.env.BASE_URL : import.meta.env.BASE_URL + '/';
  return base + path.replace(/^\//, '');
}
export const BUILD_ID = process.env.BUILD_ID || process.env.GITHUB_SHA || 'dev';
