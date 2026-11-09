import { defineConfig, devices } from '@playwright/test';

export default defineConfig({
  testDir: './e2e-preview',
  use: {
    baseURL: 'http://127.0.0.1:19091',
    trace: 'retain-on-failure',
    // Simulate the trusted TLS terminator on a loopback-only test server.
    extraHTTPHeaders: { 'X-Forwarded-Proto': 'https' },
  },
  projects: [
    { name: 'compiled-desktop', use: { ...devices['Desktop Chrome'] } },
    { name: 'compiled-iphone', use: { ...devices['iPhone 13'] } },
  ],
  webServer: {
    command: 'python -m gunicorn --chdir ../backend --bind 127.0.0.1:19091 --workers 2 config.wsgi:application',
    // Readiness probes cannot inject proxy headers; HTTP requests without them
    // correctly redirect to HTTPS. The tests below verify actual HTTP responses.
    port: 19091,
    env: {
      DJANGO_SETTINGS_MODULE: 'config.settings.team_preview',
      DJANGO_SECRET_KEY: 'synthetic-ci-preview-key-that-is-longer-than-fifty-characters',
      DJANGO_ALLOWED_HOSTS: '127.0.0.1',
    },
    gracefulShutdown: { signal: 'SIGTERM', timeout: 5000 },
  },
});
