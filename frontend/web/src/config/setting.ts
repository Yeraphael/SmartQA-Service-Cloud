import AppConfig from "@/config";
import { SystemThemeEnum, MenuThemeEnum, MenuTypeEnum, ContainerWidthEnum } from "@/enums/appEnum";
import { LayoutMode, ComponentSize, SidebarColor, ThemeMode, LanguageEnum } from "@/enums";

const env = import.meta.env;
const { pkg } = __APP_INFO__;
const prefersDark = window.matchMedia("(prefers-color-scheme: dark)").matches;

export const SETTING_DEFAULT_CONFIG = {
  name: pkg.name as string,
  title: (env.VITE_APP_TITLE as string) || "SmartQA Service Cloud",
  version: pkg.version as string,

  showSettings: false,
  showMenuSearch: false,
  showFullscreen: true,
  showSizeSelect: true,
  showLangSelect: false,
  showTagsView: true,
  showAppLogo: true,
  showGuide: false,

  layout: LayoutMode.LEFT,
  theme: prefersDark ? ThemeMode.DARK : ThemeMode.LIGHT,
  size: ComponentSize.DEFAULT,
  language: LanguageEnum.ZH_CN,
  themeColor: "#4080FF",
  sidebarColorScheme: SidebarColor.CLASSIC_BLUE,
  guideVisible: false,
  grayMode: false,
  pageSwitchingAnimation: "fade-slide",

  menuType: MenuTypeEnum.LEFT,
  menuOpenWidth: 230,
  menuOpen: true,
  dualMenuShowText: false,
  systemThemeType: prefersDark ? SystemThemeEnum.DARK : SystemThemeEnum.LIGHT,
  systemThemeMode: SystemThemeEnum.AUTO,
  menuThemeType: MenuThemeEnum.DESIGN,
  systemThemeColor: AppConfig.systemMainColor[0] ?? "#4080FF",

  showMenuButton: true,
  showFastEnter: false,
  showRefreshButton: true,
  showCrumbs: true,
  showWorkTab: true,
  showLanguage: false,
  showNprogress: true,
  showSettingGuide: false,
  showFestivalText: false,

  autoClose: false,
  uniqueOpened: true,
  colorWeak: false,
  refresh: false,
  holidayFireworksLoaded: false,

  boxBorderMode: true,
  pageTransition: "slide-left",
  tabStyle: "tab-google",
  customRadius: "0.75",
  containerWidth: ContainerWidthEnum.FULL,
  festivalDate: "",
};

export const defaultSettings = SETTING_DEFAULT_CONFIG;

export function getSettingDefaults() {
  return { ...SETTING_DEFAULT_CONFIG };
}

export function resetToDefaults(currentSettings: Record<string, any>) {
  const defaults = getSettingDefaults();
  Object.keys(defaults).forEach((key) => {
    if (key in currentSettings) {
      currentSettings[key] = defaults[key as keyof typeof defaults];
    }
  });
}

export const themeColorPresets = [
  "#4080FF",
  "#16A34A",
  "#0891B2",
  "#F97316",
  "#DC2626",
  "#7C3AED",
  "#EC4899",
  "#4B5563",
];
