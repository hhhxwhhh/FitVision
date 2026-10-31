import { fileURLToPath, URL } from 'node:url'
import { defineConfig } from 'vitest/config'
import vue from '@vitejs/plugin-vue'
import Components from 'unplugin-vue-components/vite'
import { ElementPlusResolver } from 'unplugin-vue-components/resolvers'

// Vitest shares the same alias/plugin setup as the app build so that `@/...`
// imports and `.vue` SFCs resolve identically in tests.
export default defineConfig({
  // Same on-demand Element Plus resolution as the app build, so component
  // tests see the real components instead of unresolved custom elements.
  plugins: [
    vue(),
    // `dts: false` keeps the test run from writing a throwaway component type
    // declaration next to the project root (the app build owns that file).
    Components({ dts: false, resolvers: [ElementPlusResolver({ importStyle: false })] }),
  ],
  resolve: {
    alias: {
      '@': fileURLToPath(new URL('./src', import.meta.url)),
    },
  },
  test: {
    name: 'fitvision-frontend',
    globals: true,
    environment: 'node',
    setupFiles: ['./src/test/setup.ts'],
    include: ['src/**/*.{test,spec}.{ts,tsx,vue}'],
    coverage: {
      provider: 'v8',
      reporter: ['text', 'json', 'html'],
      reportsDirectory: './coverage',
      include: ['src/**/*.{ts,vue}'],
      exclude: [
        'src/**/*.test.{ts,vue}',
        'src/**/*.spec.{ts,vue}',
        'src/test/**',
        'src/**/*.d.ts',
        'src/main.ts',
      ],
    },
  },
})
