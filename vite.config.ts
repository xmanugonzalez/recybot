import { defineConfig, loadEnv } from 'vite'
import { svelte } from '@sveltejs/vite-plugin-svelte'
import tailwindcss from '@tailwindcss/vite'

export default defineConfig(({ mode }) => {
  const env = loadEnv(mode, '.', 'RECYBOT_')
  const proxy = {
    '/api': {
      target: env.RECYBOT_BRIDGE_URL || 'http://10.199.232.50:8080',
      changeOrigin: true,
    },
  }

  return {
    plugins: [svelte(), tailwindcss()],
    server: {
      host: '0.0.0.0',
      proxy,
    },
    preview: {
      host: '0.0.0.0',
      proxy,
    },
  }
})
