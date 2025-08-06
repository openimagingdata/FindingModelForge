import { defineConfig } from 'vite'

export default defineConfig({
  build: {
    outDir: 'static',
    emptyOutDir: false, // Don't clear static dir (has CSS, images)
    rollupOptions: {
      input: {
        main: 'src/js/main.js'
      },
      output: {
        entryFileNames: 'js/[name].[hash].js',
        chunkFileNames: 'js/[name].[hash].js',
        assetFileNames: 'assets/[name].[hash].[ext]'
      }
    },
    manifest: true, // Generate manifest for FastAPI to read
    assetsDir: 'js'
  },
  publicDir: false, // We handle static assets separately
  server: {
    port: 5173,
    host: 'localhost'
  }
})
