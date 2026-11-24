import { defineConfig, devices } from '@playwright/test';

// Section 11.2 device matrix: 8 viewports. Apple devices on WebKit, Android/desktop on Chromium.
// BASE_URL lets the post-deploy smoke run target a CDN or the staging URL instead of the local preview.
const BASE_URL = process.env.BASE_URL || 'http://localhost:4321/';
const phone = (name: string, width: number, height: number, browserName: 'webkit' | 'chromium', ua: string) => ({
  name,
  use: { browserName, viewport: { width, height }, deviceScaleFactor: 2, isMobile: browserName === 'chromium' ? true : undefined, hasTouch: true, userAgent: ua },
});
const IOS_UA = devices['iPhone 15'].userAgent;
const IPAD_UA = devices['iPad Mini'].userAgent;
const ANDROID_UA = devices['Pixel 7'].userAgent;

export default defineConfig({
  testDir: 'tests',
  fullyParallel: true,
  forbidOnly: !!process.env.CI,
  retries: process.env.CI ? 1 : 0,
  reporter: process.env.CI ? [['github'], ['html', { open: 'never' }]] : [['list']],
  snapshotPathTemplate: '{testDir}/__screenshots__/{projectName}/{arg}{ext}',
  expect: { toHaveScreenshot: { maxDiffPixelRatio: 0.001, animations: 'disabled', caret: 'hide' } },
  use: { baseURL: BASE_URL, trace: 'retain-on-failure' },
  projects: [
    phone('iphone-se', 375, 667, 'webkit', IOS_UA),
    phone('iphone-15', 393, 852, 'webkit', IOS_UA),
    phone('iphone-15-pro-max', 430, 932, 'webkit', IOS_UA),
    phone('pixel-7', 412, 915, 'chromium', ANDROID_UA),
    phone('ipad-mini-portrait', 744, 1133, 'webkit', IPAD_UA),
    phone('ipad-air-landscape', 1180, 820, 'webkit', IPAD_UA),
    { name: 'desktop', use: { browserName: 'chromium', viewport: { width: 1440, height: 900 } } },
    { name: 'wide', use: { browserName: 'chromium', viewport: { width: 1920, height: 1080 } } },
    // Extra layout-only check at the smallest supported width (not part of the visual baseline set).
    { name: 'narrow-320', testMatch: /mobile\.spec\.ts/, use: { browserName: 'chromium', viewport: { width: 320, height: 640 }, isMobile: true, hasTouch: true, userAgent: ANDROID_UA } },
  ],
  webServer: process.env.BASE_URL ? undefined : { command: 'npm run preview', url: BASE_URL, reuseExistingServer: !process.env.CI, timeout: 60_000 },
});
