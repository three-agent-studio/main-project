import { defineConfig } from 'vite';
import react from '@vitejs/plugin-react';

export default defineConfig({
  plugins: [react()],
  // Keep production JS compatible with Safari 15+, not only modern desktop engines.
  build: { target: ['es2020', 'safari15'] },
  server: {
    // Same browser origin in dev and production: sessions/CSRF need no permissive CORS.
    proxy: Object.fromEntries(['/api', '/auth', '/admin', '/static', '/health'].map(
      (path) => [path, { target: 'http://127.0.0.1:8000' }],
    )),
  },
});
