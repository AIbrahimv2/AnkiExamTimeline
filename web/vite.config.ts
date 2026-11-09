import react from "@vitejs/plugin-react";
import { defineConfig } from "vite";

// The add-on loads the UI with plain <script>/<link> tags from
// /_addons/<addon>/web/, so build one IIFE bundle with fixed file names
// straight into the add-on's src/web/ folder.
export default defineConfig({
  plugins: [react()],
  base: "./",
  build: {
    outDir: "../src/web",
    emptyOutDir: true,
    cssCodeSplit: false,
    target: "chrome118",
    rollupOptions: {
      input: "src/main.tsx",
      output: {
        format: "iife",
        entryFileNames: "app.js",
        assetFileNames: "app[extname]",
      },
    },
  },
  // `npm run dev` serves index.html with live reload; bridge calls are
  // proxied to tools/devserver.py, which runs the real Python bridge.
  server: {
    port: 5174,
    proxy: { "/bridge": "http://127.0.0.1:5181" },
  },
});
