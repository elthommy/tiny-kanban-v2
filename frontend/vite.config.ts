/// <reference types="vitest/config" />
import { defineConfig, loadEnv } from 'vite'
import react from '@vitejs/plugin-react'

// Ports come from the repo-root .env (see ../.env.example):
//   KANBAN_FRONTEND_PORT — this dev server
//   KANBAN_BACKEND_PORT  — the FastAPI server /api requests are proxied to
export default defineConfig(({ mode }) => {
  const env = loadEnv(mode, '..', 'KANBAN_')
  const backendPort = env.KANBAN_BACKEND_PORT || '8000'
  return {
    plugins: [react()],
    envDir: '..',
    envPrefix: 'KANBAN_',
    server: {
      port: Number(env.KANBAN_FRONTEND_PORT || '5173'),
      proxy: {
        '/api': `http://127.0.0.1:${backendPort}`,
      },
    },
    test: {
      environment: 'jsdom',
    },
  }
})
