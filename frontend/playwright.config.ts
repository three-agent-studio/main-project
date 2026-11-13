import { defineConfig, devices } from '@playwright/test';

export default defineConfig({
  testDir: './e2e',
  use: { baseURL: 'http://127.0.0.1:5173', trace: 'retain-on-failure' },
  projects: [
    { name: 'desktop', use: { ...devices['Desktop Chrome'] } },
    { name: 'iphone-webkit', use: { ...devices['iPhone 13'], baseURL: 'http://127.0.0.2:5173' } },
    { name: 'mobile-360', use: { ...devices['Desktop Chrome'], viewport: { width: 360, height: 800 } } },
  ],
  webServer: [
    { command: 'python ../backend/manage.py runserver 127.0.0.1:8000 --noreload', url: 'http://127.0.0.1:8000/health/ready/' },
    { command: 'npm run dev:lan', url: 'http://127.0.0.1:5173' },
  ],
});
