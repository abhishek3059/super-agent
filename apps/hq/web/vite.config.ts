import { defineConfig } from 'vite';
import react from '@vitejs/plugin-react';
import { fileURLToPath } from 'node:url';

const API = `http://127.0.0.1:${Number(process.env.PORT ?? 8787)}`;

export default defineConfig({
  plugins: [react()],
  resolve: {
    alias: { '@shared': fileURLToPath(new URL('../server/src', import.meta.url)) },
  },
  server: {
    host: '127.0.0.1',
    port: 5173,
    strictPort: true,
    proxy: {
      '/api': { target: API, changeOrigin: true, ws: true },
    },
  },
  build: { target: 'es2022', chunkSizeWarningLimit: 1200 },
});
