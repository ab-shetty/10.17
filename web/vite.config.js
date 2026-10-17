import { defineConfig } from 'vite';

// Serve the committed shared/ contracts as static files at the site root (/daily.json, /replay/...).
// appType 'mpa' disables the SPA fallback so a missing contract file is a real 404.
export default defineConfig({
  publicDir: '../shared',
  appType: 'mpa',
  server: { port: 5173 },
});
