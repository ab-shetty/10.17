import { defineConfig } from 'vite';

// shared/ is the contract folder between A and B: serve it as the static root so the app reads
// /daily.json, /preds.json, /replay/<day>.json directly. appType 'mpa' makes missing files 404
// instead of falling back to index.html, which the real-then-mock loader relies on.
export default defineConfig({
  base: './',
  publicDir: '../shared',
  appType: 'mpa',
  server: { host: true },
});
