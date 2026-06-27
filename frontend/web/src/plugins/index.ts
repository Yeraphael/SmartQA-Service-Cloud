import type { App } from "vue";
import { initGlobDirectives } from "@/directives";
import { initI18n } from "@/locales";
import { initRouter } from "@/router";
import { initStore } from "@stores";
import { initErrorHandle } from "@utils";
import { initElementPlus } from "./element-plus";
import { initElIcons } from "./icons";
import { initIconify } from "./iconify";

export async function initPlugins(app: App<Element>): Promise<void> {
  initElIcons(app);
  initIconify();
  initStore(app);
  await initRouter(app);
  initGlobDirectives(app);
  initErrorHandle(app);
  initI18n(app);
  initElementPlus(app);
}
