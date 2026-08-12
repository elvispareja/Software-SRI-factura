import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

// https://vite.dev/config/
export default defineConfig({
  plugins: [react()],
  test: {
    // El entorno por defecto es `node`: la mayor parte de lo que se prueba es
    // lógica pura y arrancar jsdom en cada archivo cuesta segundos. Los pocos
    // archivos que necesitan DOM lo piden con `@vitest-environment jsdom`.
    environment: 'node',
    include: ['src/**/*.test.{js,jsx}'],
    globals: true,
    // Un único hilo: el proyecto vive en una carpeta sincronizada y arrancar
    // varios procesos sobre ella hace que los workers no respondan a tiempo.
    pool: 'threads',
    maxWorkers: 1,
    minWorkers: 1,
    testTimeout: 20000,
    hookTimeout: 30000,
    // El proyecto vive en una carpeta sincronizada, donde leer cientos de
    // archivos sueltos de node_modules cuesta decenas de segundos. Vitest
    // aborta el worker si tarda más de 60 s en arrancar (límite fijo en su
    // código), así que se pre-empaquetan las dependencias del entorno DOM
    // para que sean unas pocas lecturas en vez de miles.
    deps: {
      optimizer: {
        web: {
          enabled: true,
          include: [
            'react',
            'react-dom',
            'react-router-dom',
            '@testing-library/react',
            '@testing-library/user-event',
            'framer-motion',
            'lucide-react',
            'recharts',
          ],
        },
      },
    },
  },
})
