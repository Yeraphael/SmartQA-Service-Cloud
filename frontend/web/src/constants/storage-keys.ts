export const ACCESS_TOKEN_KEY = "access_token";
export const REFRESH_TOKEN_KEY = "refresh_token";
export const REMEMBER_ME_KEY = "remember_me";

export const SHOW_TAGS_VIEW_KEY = "showTagsView";
export const SHOW_APP_LOGO_KEY = "showAppLogo";
export const SHOW_SETTINGS_KEY = "showSettings";
export const SHOW_FULLSCREEN_KEY = "showFullscreen";
export const SHOW_LANG_SELECT_KEY = "showLangSelect";
export const LAYOUT_KEY = "layout";
export const SIDEBAR_COLOR_SCHEME_KEY = "sidebarColorScheme";
export const THEME_KEY = "theme";
export const THEME_COLOR_KEY = "themeColor";
export const GRAY_MODE_KEY = "grayMode";
export const PAGE_SWITCHING_ANIMATION_KEY = "pageSwitchingAnimation";

export const ROLE_ROOT = "ADMIN";

export const AUTH_KEYS = {
  ACCESS_TOKEN: ACCESS_TOKEN_KEY,
  REFRESH_TOKEN: REFRESH_TOKEN_KEY,
  REMEMBER_ME: REMEMBER_ME_KEY,
} as const;

export const SETTINGS_KEYS = {
  SHOW_TAGS_VIEW: SHOW_TAGS_VIEW_KEY,
  SHOW_APP_LOGO: SHOW_APP_LOGO_KEY,
  SHOW_SETTINGS: SHOW_SETTINGS_KEY,
  SHOW_FULLSCREEN: SHOW_FULLSCREEN_KEY,
  SHOW_LANG_SELECT: SHOW_LANG_SELECT_KEY,
  SIDEBAR_COLOR_SCHEME: SIDEBAR_COLOR_SCHEME_KEY,
  LAYOUT: LAYOUT_KEY,
  THEME_COLOR: THEME_COLOR_KEY,
  THEME: THEME_KEY,
  GRAY_MODE: GRAY_MODE_KEY,
  PAGE_SWITCHING_ANIMATION: PAGE_SWITCHING_ANIMATION_KEY,
} as const;

export const ALL_STORAGE_KEYS = {
  ...AUTH_KEYS,
  ...SETTINGS_KEYS,
} as const;
