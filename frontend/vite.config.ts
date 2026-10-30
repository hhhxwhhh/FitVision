import { fileURLToPath, URL } from 'node:url'
import { defineConfig, loadEnv } from 'vite'
import vue from '@vitejs/plugin-vue'

// https://vite.dev/config/
export default defineConfig(({ mode }) => {
  const env = loadEnv(mode, process.cwd(), '')
  const proxyTarget = env.VITE_DEV_PROXY_TARGET || 'http://127.0.0.1:8000'

  return {
    plugins: [vue()],
    resolve: {
      alias: {
        '@': fileURLToPath(new URL('./src', import.meta.url)),
      },
    },
    server: {
      port: 5173,
      proxy: {
        // Keeps the frontend free of hard-coded backend URLs in development.
        '/api': { target: proxyTarget, changeOrigin: true },
        '/media': { target: proxyTarget, changeOrigin: true },
        '/static': { target: proxyTarget, changeOrigin: true },
      },
    },
    build: {
      // Long-lived vendor chunks improve caching across app releases.
      rollupOptions: {
        output: {
          manualChunks: {
            'vue-vendor': ['vue', 'vue-router', 'pinia'],
            'element-plus': ['element-plus'],
            charts: ['echarts', 'vue-echarts'],
            mediapipe: ['@mediapipe/pose', '@mediapipe/camera_utils', '@mediapipe/drawing_utils'],
          },
        },
      },
      chunkSizeWarningLimit: 1200,
    },
  }
})
