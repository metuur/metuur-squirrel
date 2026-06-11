import { defineConfig } from 'vite';
import react from '@vitejs/plugin-react';
import tailwindcss from '@tailwindcss/vite';
import path from 'node:path';

// Vite config for the Squirrel React SPA.
// - Aliases @/ -> src/
// - Emits to ./dist (read by ../server.py)
// - Dev proxy forwards /api/* to the running Python server on :3939
export default defineConfig({
  resolve: {
    alias: { '@': path.resolve(__dirname, './src') },
  },
  server: {
    port: 5173,
    proxy: {
      // Overridable so dev can target a non-prod backend port (e.g. :3942)
      // and avoid colliding with the installed app on :3939. Defaults to :3939.
      '/api': process.env.VITE_SQUIRREL_BACKEND_ORIGIN ?? 'http://127.0.0.1:3939',
    },
  },
  build: {
    outDir: 'dist',
    emptyOutDir: true,
    sourcemap: false,
    chunkSizeWarningLimit: 600,
  },
  plugins: [react(), tailwindcss()],
});
