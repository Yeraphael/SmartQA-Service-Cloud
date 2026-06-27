/// <reference types="vite/client" />

declare module "nprogress";
declare module "vue-img-cutter";

declare const __APP_VERSION__: string;
declare const __APP_NAME__: string;
declare const __APP_INFO__: {
  pkg: {
    name: string;
    version: string;
    engines: Record<string, string>;
    dependencies: Record<string, string>;
    devDependencies: Record<string, string>;
  };
  buildTimestamp: number;
};
