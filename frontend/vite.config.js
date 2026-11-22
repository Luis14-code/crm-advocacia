import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";

export default defineConfig({
  plugins: [react()],
  server: {
    host: true,
    port: 5173,
    // Docker + Windows: inotify não cruza o bind mount, então usa polling para o HMR.
    watch: { usePolling: true, interval: 300 },
  },
});
