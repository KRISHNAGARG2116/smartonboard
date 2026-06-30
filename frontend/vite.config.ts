import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";
import tailwindcss from "@tailwindcss/vite";
import path from "path";

export default defineConfig({
  plugins: [react(), tailwindcss()],
  resolve: {
    alias: {
      "motion/react": "framer-motion",
      "@/components": path.resolve(__dirname, "./src/components/landing"),
      "@": path.resolve(__dirname, "./src"),
    },
  },
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
        target: "http://127.0.0.1:8000",
        changeOrigin: true,
      },
    },
  },
});
