import type { App } from "vue";
import { createPinia } from "pinia";
import piniaPluginPersistedstate from "pinia-plugin-persistedstate";
import { useUserStore } from "./modules/user.store";
import { useConfigStore } from "./modules/config.store";
import { useWorktabStore } from "./modules/worktab.store";

const store = createPinia();

store.use(piniaPluginPersistedstate);

export function initStore(app: App<Element>) {
  app.use(store);
}

export * from "./modules/app.store";
export * from "./modules/config.store";
export * from "./modules/menu.store";
export * from "./modules/setting.store";
export * from "./modules/user.store";
export * from "./modules/worktab.store";

export { store };

export interface RefreshCacheOptions {
  refreshUser?: boolean;
  refreshRoutes?: boolean;
  refreshConfig?: boolean;
  clearTags?: boolean;
}

export async function refreshAppCaches(opts: RefreshCacheOptions = {}) {
  const {
    refreshUser = true,
    refreshRoutes = true,
    refreshConfig = true,
    clearTags = false,
  } = opts;

  const userStore = useUserStore(store);
  const configStore = useConfigStore(store);

  const tasks: Promise<any>[] = [];

  if (refreshUser) {
    tasks.push(userStore.getUserInfo());
  }
  if (refreshConfig) {
    tasks.push(configStore.getConfig(true));
  }

  await Promise.allSettled(tasks);

  if (refreshRoutes) {
    const { refreshMenuAndRoutes } = await import("@/router/beforeEach");
    await refreshMenuAndRoutes();
  }

  if (clearTags) {
    useWorktabStore(store).clearAll();
  }
}
