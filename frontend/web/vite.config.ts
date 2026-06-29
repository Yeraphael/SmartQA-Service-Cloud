import vue from "@vitejs/plugin-vue";
import tailwindcss from "@tailwindcss/vite";
import autoprefixer from "autoprefixer";
import { defineConfig, loadEnv } from "vite";
import viteCompression from "vite-plugin-compression";
import path from "node:path";
import { fileURLToPath } from "node:url";
import { name, version } from "./package.json";

const __dirname = path.dirname(fileURLToPath(import.meta.url));

export default ({ mode }: { mode: string }) => {
  const env = loadEnv(mode, process.cwd());
  const baseApi = env.VITE_APP_BASE_API || "/api/v1";

  return defineConfig({
    base: env.VITE_BASE_URL || "/",
    define: {
      __APP_VERSION__: JSON.stringify(env.VITE_VERSION || version),
      __APP_NAME__: JSON.stringify(env.VITE_APP_TITLE || "SmartQA Service Cloud"),
      __APP_INFO__: JSON.stringify({
        pkg: { name, version },
        buildTimestamp: Date.now(),
      }),
    },
    server: {
      host: true,
      port: Number(env.VITE_PORT || 5180),
      open: false,
      proxy: {
        [baseApi]: {
          target: env.VITE_API_BASE_URL || "http://127.0.0.1:8001",
          secure: false,
          changeOrigin: true,
        },
      },
    },
    resolve: {
      alias: {
        "@": resolvePath("src"),
        "@fa_imgs": resolvePath("src/assets/fa_imgs"),
        "@fa_imgs/*": resolvePath("src/assets/fa_imgs/*"),
      },
    },
    build: {
      target: "es2022",
      outDir: "dist",
      chunkSizeWarningLimit: 2400,
      rollupOptions: {
        output: {
          manualChunks: {
            vue: ["vue"],
            "element-plus": ["element-plus"],
            axios: ["axios"],
          },
          entryFileNames: "js/[name].[hash].js",
          chunkFileNames: "js/[name].[hash].js",
          assetFileNames: "assets/[name].[hash].[ext]",
        },
      },
    },
    plugins: [
      vue(),
      tailwindcss(),
      viteCompression({
        verbose: false,
        disable: false,
        algorithm: "gzip",
        ext: ".gz",
        threshold: 10240,
        deleteOriginFile: false,
      }),
    ],
    optimizeDeps: {
      include: ["vue", "axios", "element-plus", "@element-plus/icons-vue"],
    },
    css: {
      postcss: {
        plugins: [autoprefixer()],
      },
    },
  });
};

function resolvePath(paths: string) {
  return path.resolve(__dirname, paths);
}
