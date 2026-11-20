import { defineConfig } from 'astro/config';
import react from '@astrojs/react';
import tailwindcss from '@tailwindcss/vite';

// Static output. BASE_PATH is for hosting under a sub-path (the same convention as the game's own config).
export default defineConfig({
  base: process.env.BASE_PATH ?? '/',
  integrations: [react()],
  vite: { plugins: [tailwindcss()] },
});
