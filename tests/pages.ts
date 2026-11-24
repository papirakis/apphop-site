// Templates covered by visual, a11y and mobile checks (one instance of each template).
export const PAGES = [
  { name: 'home', path: '' },
  { name: 'apps', path: 'apps/' },
  { name: 'app', path: 'apps/roommeasure/' },
  { name: 'support', path: 'apps/roommeasure/support/' },
  { name: 'privacy', path: 'apps/tendril/privacy/' },
  { name: 'press', path: 'press/' },
  { name: 'about', path: 'about/' },
  { name: 'contact', path: 'contact/' },
  { name: '404', path: '404.html' },
];
// Every generated route, for the horizontal-scroll check.
export const ALL_PATHS = [
  '', 'apps/', 'press/', 'about/', 'contact/', 'privacy/', 'legal/', '404.html',
  ...['roommeasure', 'tendril', 'gear-bins'].flatMap((s) => [`apps/${s}/`, `apps/${s}/support/`, `apps/${s}/privacy/`]),
];
