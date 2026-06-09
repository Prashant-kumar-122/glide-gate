import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'
import { VitePWA } from 'vite-plugin-pwa'

export default defineConfig({
  plugins: [
    react(),
    VitePWA({
      strategies: 'injectManifest',
      srcDir: 'src',
      filename: 'sw.ts',
      // registerType: 'prompt' + injectRegister: null — we register manually via
      // useServiceWorkerUpdate so we can show a non-dismissible update banner.
      registerType: 'prompt',
      injectRegister: null,
      // External manifest.webmanifest — set manifest:false so the plugin doesn't
      // generate its own; we link it manually in index.html.
      manifest: false,
      devOptions: {
        enabled: false,
      },
      injectManifest: {
        // Precache Vite build outputs (JS/CSS/fonts/woff2) but exclude heavy
        // vendor chunks that bloat the precache without improving offline UX.
        globPatterns: ['**/*.{js,css,html,woff2,svg,png,ico}'],
        maximumFileSizeToCacheInBytes: 3_000_000,
        globIgnores: [
          '**/ag-grid*',
          '**/@xyflow*',
          '**/workbox-*',
        ],
      },
    }),
  ],
  server: {
    port: 5173,
    proxy: {
      '/api': {
        target: process.env.VITE_API_URL || 'http://localhost:8000',
        changeOrigin: true,
      },
      '/socket.io': {
        target: process.env.VITE_API_URL || 'http://localhost:8000',
        changeOrigin: true,
        ws: true,
      },
    },
  },
  preview: {
    port: 4173,
    proxy: {
      '/api': {
        target: process.env.VITE_API_URL || 'http://localhost:8000',
        changeOrigin: true,
      },
      '/socket.io': {
        target: process.env.VITE_API_URL || 'http://localhost:8000',
        changeOrigin: true,
        ws: true,
      },
    },
  },
  resolve: {
    alias: {
      '@': '/src',
    },
  },
})
