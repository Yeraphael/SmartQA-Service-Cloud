import { computed, ref, watch } from "vue";
import type { Ref } from "vue";
import { defineStore } from "pinia";
import { useStorage } from "@vueuse/core";
import AppConfig from "@/config";
import { SETTING_DEFAULT_CONFIG, defaultSettings } from "@/config/setting";
import { ContainerWidthEnum, MenuThemeEnum, MenuTypeEnum, SystemThemeEnum } from "@/enums/appEnum";
import type { LayoutMode } from "@/enums/settings/layout.enum";
import { SidebarColor, ThemeMode } from "@/enums/settings/theme.enum";
import type { MenuThemeType } from "@/types/store";
import { SETTINGS_KEYS } from "@/constants";
import {
  StorageConfig,
  applyTheme,
  generateThemeColors,
  setElementThemeColor,
  toggleDarkMode,
  toggleSidebarColor,
} from "@utils";

export const useSettingsStore = defineStore(
  "settingStore",
  () => {
    const menuType = ref(SETTING_DEFAULT_CONFIG.menuType);
    const menuOpenWidth = ref(SETTING_DEFAULT_CONFIG.menuOpenWidth);
    const menuOpen = ref(SETTING_DEFAULT_CONFIG.menuOpen);
    const dualMenuShowText = ref(SETTING_DEFAULT_CONFIG.dualMenuShowText);

    const systemThemeType = ref(SETTING_DEFAULT_CONFIG.systemThemeType);
    const systemThemeMode = ref(SETTING_DEFAULT_CONFIG.systemThemeMode);
    const menuThemeType = ref(SETTING_DEFAULT_CONFIG.menuThemeType);
    const systemThemeColor = ref(SETTING_DEFAULT_CONFIG.systemThemeColor);

    const showMenuButton = ref(SETTING_DEFAULT_CONFIG.showMenuButton);
    const showRefreshButton = ref(SETTING_DEFAULT_CONFIG.showRefreshButton);
    const showCrumbs = ref(SETTING_DEFAULT_CONFIG.showCrumbs);
    const showWorkTab = ref(SETTING_DEFAULT_CONFIG.showWorkTab);
    const showLanguage = ref(SETTING_DEFAULT_CONFIG.showLanguage);
    const showNprogress = ref(SETTING_DEFAULT_CONFIG.showNprogress);

    const autoClose = ref(SETTING_DEFAULT_CONFIG.autoClose);
    const uniqueOpened = ref(SETTING_DEFAULT_CONFIG.uniqueOpened);
    const colorWeak = ref(SETTING_DEFAULT_CONFIG.colorWeak);
    const refresh = ref(SETTING_DEFAULT_CONFIG.refresh);

    const boxBorderMode = ref(SETTING_DEFAULT_CONFIG.boxBorderMode);
    const pageTransition = ref(SETTING_DEFAULT_CONFIG.pageTransition);
    const tabStyle = ref(SETTING_DEFAULT_CONFIG.tabStyle);
    const customRadius = ref(SETTING_DEFAULT_CONFIG.customRadius);
    const containerWidth = ref(SETTING_DEFAULT_CONFIG.containerWidth);

    const settingsVisible = ref(false);

    const showTagsView = useStorage<boolean>(
      SETTINGS_KEYS.SHOW_TAGS_VIEW,
      defaultSettings.showTagsView
    );
    const showAppLogo = useStorage<boolean>(
      SETTINGS_KEYS.SHOW_APP_LOGO,
      defaultSettings.showAppLogo
    );
    const showSettings = useStorage<boolean>(
      SETTINGS_KEYS.SHOW_SETTINGS,
      defaultSettings.showSettings
    );
    const showFullscreen = useStorage<boolean>(
      SETTINGS_KEYS.SHOW_FULLSCREEN,
      defaultSettings.showFullscreen
    );
    const showLangSelect = useStorage<boolean>(
      SETTINGS_KEYS.SHOW_LANG_SELECT,
      defaultSettings.showLangSelect
    );
    const sidebarColorScheme = useStorage<string>(
      SETTINGS_KEYS.SIDEBAR_COLOR_SCHEME,
      defaultSettings.sidebarColorScheme
    );
    const layout = useStorage<LayoutMode>(
      SETTINGS_KEYS.LAYOUT,
      defaultSettings.layout as LayoutMode
    );
    const themeColor = useStorage<string>(SETTINGS_KEYS.THEME_COLOR, defaultSettings.themeColor);
    const theme = useStorage<ThemeMode>(SETTINGS_KEYS.THEME, defaultSettings.theme);
    const grayMode = useStorage<boolean>(SETTINGS_KEYS.GRAY_MODE, defaultSettings.grayMode);
    const pageSwitchingAnimation = useStorage<string>(
      SETTINGS_KEYS.PAGE_SWITCHING_ANIMATION,
      defaultSettings.pageSwitchingAnimation
    );

    const getMenuTheme = computed((): MenuThemeType => {
      if (isDark.value) return AppConfig.darkMenuStyles[0]!;
      return (
        AppConfig.themeList.find((item) => item.theme === menuThemeType.value) ??
        AppConfig.themeList[0]!
      );
    });

    const isDark = computed(() => systemThemeType.value === SystemThemeEnum.DARK);
    const getMenuOpenWidth = computed(() => `${menuOpenWidth.value}px`);
    const getCustomRadius = computed(() => `${customRadius.value}rem`);

    const settingsMap = {
      showTagsView,
      showAppLogo,
      showSettings,
      showFullscreen,
      showLangSelect,
      sidebarColorScheme,
      layout,
      themeColor,
      theme,
      grayMode,
      pageSwitchingAnimation,
    } as const;

    watch(
      [theme, themeColor],
      ([newTheme, newThemeColor]) => {
        toggleDarkMode(newTheme === ThemeMode.DARK);
        applyTheme(generateThemeColors(newThemeColor, newTheme));
      },
      { immediate: true }
    );

    watch(
      sidebarColorScheme,
      (newSidebarColorScheme) => {
        toggleSidebarColor(newSidebarColorScheme === SidebarColor.CLASSIC_BLUE);
      },
      { immediate: true }
    );

    watch(
      grayMode,
      (value) => {
        document.documentElement.style.filter = value ? "grayscale(100%)" : "";
      },
      { immediate: true }
    );

    const switchMenuLayouts = (type: MenuTypeEnum) => {
      menuType.value = type;
    };
    const setMenuOpenWidth = (width: number) => {
      menuOpenWidth.value = width;
    };
    const setGlopTheme = (themeType: SystemThemeEnum, themeMode: SystemThemeEnum) => {
      systemThemeType.value = themeType;
      systemThemeMode.value = themeMode;
      localStorage.setItem(StorageConfig.THEME_KEY, themeType);
    };
    const switchMenuStyles = (menuTheme: MenuThemeEnum) => {
      menuThemeType.value = menuTheme;
    };
    const setElementTheme = (color: string) => {
      systemThemeColor.value = color;
      setElementThemeColor(color);
    };
    const setBorderMode = () => {
      boxBorderMode.value = !boxBorderMode.value;
    };
    const setContainerWidth = (width: ContainerWidthEnum) => {
      containerWidth.value = width;
    };
    const setUniqueOpened = () => {
      uniqueOpened.value = !uniqueOpened.value;
    };
    const setButton = () => {
      showMenuButton.value = !showMenuButton.value;
    };
    const setAutoClose = () => {
      autoClose.value = !autoClose.value;
    };
    const setShowRefreshButton = () => {
      showRefreshButton.value = !showRefreshButton.value;
    };
    const setCrumbs = () => {
      showCrumbs.value = !showCrumbs.value;
    };
    const setWorkTab = (show: boolean) => {
      showWorkTab.value = show;
    };
    const setLanguage = () => {
      showLanguage.value = !showLanguage.value;
    };
    const setNprogress = () => {
      showNprogress.value = !showNprogress.value;
    };
    const setColorWeak = () => {
      colorWeak.value = !colorWeak.value;
    };
    const setPageTransition = (transition: string) => {
      pageTransition.value = transition;
    };
    const setTabStyle = (style: string) => {
      tabStyle.value = style;
    };
    const setMenuOpen = (open: boolean) => {
      menuOpen.value = open;
    };
    const reload = () => {
      refresh.value = !refresh.value;
    };
    const setCustomRadius = (radius: string) => {
      customRadius.value = radius;
      document.documentElement.style.setProperty("--custom-radius", `${radius}rem`);
    };
    const setDualMenuShowText = (show: boolean) => {
      dualMenuShowText.value = show;
    };

    function updateSetting<K extends keyof typeof settingsMap>(
      key: K,
      value: boolean | string
    ): void {
      (settingsMap[key] as Ref<any>).value = value;
    }
    function updateTheme(newTheme: ThemeMode): void {
      theme.value = newTheme;
    }
    function updateThemeColor(newColor: string): void {
      themeColor.value = newColor;
    }
    function updateSidebarColorScheme(newScheme: string): void {
      sidebarColorScheme.value = newScheme;
    }
    function updateLayout(newLayout: LayoutMode): void {
      layout.value = newLayout;
    }
    function toggleSettingsPanel(): void {
      settingsVisible.value = !settingsVisible.value;
    }
    function showSettingsPanel(): void {
      settingsVisible.value = true;
    }
    function hideSettingsPanel(): void {
      settingsVisible.value = false;
    }
    function updateGrayMode(newValue: boolean): void {
      grayMode.value = newValue;
    }
    function updatePageSwitchingAnimation(newValue: string): void {
      pageSwitchingAnimation.value = newValue;
    }
    function resetSettings(): void {
      showTagsView.value = defaultSettings.showTagsView;
      showAppLogo.value = defaultSettings.showAppLogo;
      showSettings.value = defaultSettings.showSettings;
      showFullscreen.value = defaultSettings.showFullscreen;
      showLangSelect.value = defaultSettings.showLangSelect;
      sidebarColorScheme.value = defaultSettings.sidebarColorScheme;
      layout.value = defaultSettings.layout as LayoutMode;
      themeColor.value = defaultSettings.themeColor;
      theme.value = defaultSettings.theme;
      grayMode.value = defaultSettings.grayMode;
      pageSwitchingAnimation.value = defaultSettings.pageSwitchingAnimation;
    }

    return {
      menuType,
      menuOpenWidth,
      menuOpen,
      dualMenuShowText,
      systemThemeType,
      systemThemeMode,
      menuThemeType,
      systemThemeColor,
      showMenuButton,
      showRefreshButton,
      showCrumbs,
      showWorkTab,
      showLanguage,
      showNprogress,
      autoClose,
      uniqueOpened,
      colorWeak,
      refresh,
      boxBorderMode,
      pageTransition,
      tabStyle,
      customRadius,
      containerWidth,
      settingsVisible,
      showTagsView,
      showAppLogo,
      showSettings,
      showFullscreen,
      showLangSelect,
      sidebarColorScheme,
      layout,
      themeColor,
      theme,
      grayMode,
      pageSwitchingAnimation,
      getMenuTheme,
      isDark,
      getMenuOpenWidth,
      getCustomRadius,
      switchMenuLayouts,
      setMenuOpenWidth,
      setGlopTheme,
      switchMenuStyles,
      setElementTheme,
      setBorderMode,
      setContainerWidth,
      setUniqueOpened,
      setButton,
      setAutoClose,
      setShowRefreshButton,
      setCrumbs,
      setWorkTab,
      setLanguage,
      setNprogress,
      setColorWeak,
      setPageTransition,
      setTabStyle,
      setMenuOpen,
      reload,
      setCustomRadius,
      setDualMenuShowText,
      updateSetting,
      updateTheme,
      updateThemeColor,
      updateSidebarColorScheme,
      updateLayout,
      toggleSettingsPanel,
      showSettingsPanel,
      hideSettingsPanel,
      updateGrayMode,
      updatePageSwitchingAnimation,
      resetSettings,
    };
  },
  {
    persist: {
      key: "setting",
      storage: localStorage,
    },
  }
);
