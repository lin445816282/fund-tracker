import { defineConfig } from 'vite'
import vue from '@vitejs/plugin-vue'

export default defineConfig({
  plugins: [vue()],
  base: '/fund/',
  server: {
    proxy: {
      '/api': 'http://127.0.0.1:8005'
    }
  },
  build: {
    rollupOptions: {
      output: {
        manualChunks(id) {
          if (id.includes('node_modules/vant')) return 'vant'
        }
      }
    }
  }
})
