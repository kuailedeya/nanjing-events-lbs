import { defineConfig } from 'vite'
import vue from '@vitejs/plugin-vue'

export default defineConfig({
  plugins: [vue()],
  server: {
    port: 5173,
    proxy: {
      '/api': {
        target: 'http://127.0.0.1:8765',
        changeOrigin: true
      }
    }
  },
  build: {
    outDir: 'dist',
    emptyOutDir: true,
    rollupOptions: {
      output: {
        manualChunks(id) {
          if (id.includes('node_modules/echarts') || id.includes('node_modules/zrender')) {
            return 'echarts-vendor';
          }
          if (id.includes('node_modules/leaflet')) {
            return 'leaflet-vendor';
          }
          if (id.includes('node_modules/lucide-vue-next')) {
            return 'lucide-vendor';
          }
        }
      }
    }
  }
})
