import vue from '@vitejs/plugin-vue'
import { defineConfig } from 'vitest/config'

export default defineConfig({
  plugins: [vue()],
  server: {
    port: 5173,
    proxy: {
      '/api': 'http://localhost:8000',
    },
  },
  preview: {
    proxy: {
      '/api': 'http://localhost:8000',
    },
  },
  build: {
    // Inline the 48 kB Inter latin woff2 (and primeicons) as data URIs so the
    // webfont is available before first paint and a font swap can never shift
    // the layout. Larger subsets (latin-ext etc.) stay external.
    assetsInlineLimit: 50000,
  },
  test: {
    environment: 'node',
    include: ['src/**/*.test.ts'],
  },
})
