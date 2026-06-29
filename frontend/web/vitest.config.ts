import { defineConfig } from "vitest/config";
import vue from "@vitejs/plugin-vue";
import path from "node:path";

export default defineConfig({
  plugins: [vue()],
  define: {
    __APP_VERSION__: JSON.stringify("1.1.0"),
    __APP_NAME__: JSON.stringify("SmartQA Service Cloud"),
    __APP_INFO__: JSON.stringify({
      pkg: {
        name: "smartqa-service-cloud-web",
        version: "1.1.0",
      },
      buildTimestamp: 0,
    }),
  },
  resolve: {
    alias: {
      "@": path.resolve(__dirname, "src"),
      "@views": path.resolve(__dirname, "src/views"),
      "@imgs": path.resolve(__dirname, "src/assets/images"),
      "@utils": path.resolve(__dirname, "src/utils"),
      "@stores": path.resolve(__dirname, "src/store"),
    },
  },
  test: {
    globals: true,
    environment: "jsdom",
    setupFiles: ["src/__tests__/setup.ts"],
    include: ["src/**/*.{test,spec}.{ts,js}"],
  },
});
