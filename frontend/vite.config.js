import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'
import { VitePWA } from 'vite-plugin-pwa'

export default defineConfig({
  plugins: [
    react(),
    VitePWA({
      registerType: 'autoUpdate',
      devOptions: {
        enabled: true 
      },
      manifest: {
        id: '/', // <--- Fixes the ID warning
        name: 'AI Forex Screener',
        short_name: 'FX Screener',
        description: 'Live AI-powered forex technical and sentiment analysis',
        theme_color: '#0f172a', 
        background_color: '#0f172a',
        display: 'standalone', 
        icons: [
          {
            src: 'icon-192.png', // Removed the leading slash to help Vite find it
            sizes: '192x192',
            type: 'image/png'
          },
          {
            src: 'icon-512.png',
            sizes: '512x512',
            type: 'image/png'
          }
        ],
        // Fixes the "Richer UI Screenshot" warnings by using your icons as placeholders
        screenshots: [
          {
            src: 'icon-512.png',
            sizes: '512x512',
            type: 'image/png',
            form_factor: 'wide'
          },
          {
            src: 'icon-512.png',
            sizes: '512x512',
            type: 'image/png',
            form_factor: 'narrow'
          }
        ]
      }
    })
  ],
})