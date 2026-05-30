import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";

export default defineConfig({
  plugins: [react()],
  server: {
    host: "0.0.0.0",
    port: 5000,
    allowedHosts: [
      "7aebf6d8-6aae-4c16-bc37-bd2d56b54acc-00-17f4welog9mmr.sisko.replit.dev",
      ".replit.dev",
      "localhost",
    ],
    proxy: {
      "/api": {
        target: "http://localhost:8000",
        changeOrigin: true,
      },
    },
  },
});
