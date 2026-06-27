/** SmartQA configuration type definitions. */

import { MenuTypeEnum, SystemThemeEnum } from "@/enums/appEnum";
import { MenuThemeType, SystemThemeTypes } from "@/types/store";

export interface ThemeSetting {
  name: string;
  theme: SystemThemeEnum;
  color: string[];
  leftLineColor: string;
  rightLineColor: string;
  img?: string;
}

export interface MenuLayout {
  name: string;
  value: MenuTypeEnum;
  img?: string;
  description?: string;
}

export interface SystemBasicConfig {
  name: string;
  description?: string;
  logo?: string;
  favicon?: string;
  copyright?: string;
}

export interface SystemConfig {
  systemInfo: SystemBasicConfig;
  systemThemeStyles: SystemThemeTypes;
  settingThemeList: ThemeSetting[];
  menuLayoutList: MenuLayout[];
  themeList: MenuThemeType[];
  darkMenuStyles: MenuThemeType[];
  systemMainColor: readonly string[];
  headerBar?: HeaderBarFeatureConfig;
}

export interface EnvConfig {
  NODE_ENV: string;
  VITE_VERSION: string;
  VITE_PORT: string;
  VITE_BASE_URL: string;
  VITE_API_URL: string;
  VITE_USE_MOCK?: string;
  VITE_USE_GZIP?: string;
  VITE_USE_CDN?: string;
}

export interface AppConfig extends SystemConfig {
  env: EnvConfig;
  isDev: boolean;
  isProd: boolean;
  isTest: boolean;
}

export interface FeatureConfigItem {
  enabled: boolean;
  description: string;
}

export interface HeaderBarFeatureConfig {
  menuButton: FeatureConfigItem;
  refreshButton: FeatureConfigItem;
  breadcrumb: FeatureConfigItem;
  fullscreen: FeatureConfigItem;
  language: FeatureConfigItem;
  settings: FeatureConfigItem;
  themeToggle: FeatureConfigItem;
}
