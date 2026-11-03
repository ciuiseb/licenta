import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

export default defineConfig({
    plugins: [react()],
    server: {
        proxy: {
            '/api': {
                target: 'http://130.61.100.88:5000',
                changeOrigin: true,
                secure: false,
            }
        }
    }
})