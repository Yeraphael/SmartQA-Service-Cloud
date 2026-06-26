<!-- 椤堕儴鏍?-->
<template>
  <div
    class="w-full bg-(--default-bg-color)"
    :class="[
      tabStyle === 'tab-card' || tabStyle === 'tab-google' || tabStyle === 'tab-default'
        ? 'max-sm:mb-3 bg-box!'
        : '',
    ]"
  >
    <div
      class="relative box-border flex justify-between h-15 leading-15 select-none"
      :class="[
        tabStyle === 'tab-card' || tabStyle === 'tab-google' || tabStyle === 'tab-default'
          ? 'border-b border-(--fa-card-border)'
          : '',
      ]"
    >
      <div class="flex items-center flex-1 min-w-0 leading-15" :style="{ display: 'flex' }">
        <!-- 绯荤粺淇℃伅锛歀ogo + 鏍囬涓€骞跺彈銆屾樉绀哄簲鐢?Logo銆嶆帶鍒?-->
        <div
          class="flex items-center cursor-pointer"
          @click="toHome"
          v-if="isTopMenu && showAppLogo"
        >
          <FaLogo class="pl-4.5" :src="headerLogoSrc" />
          <p v-if="width >= 1400" class="my-0 mx-2 ml-2 text-lg">{{ headerSystemName }}</p>
        </div>

        <FaLogo
          v-if="showAppLogo"
          class="hidden! pl-3.5 overflow-hidden align-[-0.15em] fill-current"
          :src="headerLogoSrc"
          @click="toHome"
        />

        <!-- 鑿滃崟鎸夐挳 -->
        <FaIconButton
          v-if="isLeftMenu && shouldShowMenuButton"
          icon="ri:menu-2-fill"
          class="ml-3 max-sm:ml-[7px]"
          @click="visibleMenu"
        />

        <!-- 鍒锋柊鎸夐挳 -->
        <FaIconButton
          v-if="shouldShowRefreshButton"
          icon="ri:refresh-line"
          class="ml-3! refresh-btn max-sm:hidden!"
          :style="{ marginLeft: !isLeftMenu ? '10px' : '0' }"
          @click="reload"
        />

        <!-- 蹇€熷叆鍙?-->
        <FaFastEnter v-if="shouldShowFastEnter && width >= headerBarFastEnterMinWidth">
          <FaIconButton icon="ri:function-line" class="ml-3" />
        </FaFastEnter>

        <!-- 闈㈠寘灞?-->
        <FaBreadcrumb
          v-if="(shouldShowBreadcrumb && isLeftMenu) || (shouldShowBreadcrumb && isDualMenu)"
        />

        <!-- 椤堕儴鑿滃崟 -->
        <FaHorizontalMenu v-if="isTopMenu" :list="menuList" />

        <!-- 娣峰悎鑿滃崟-椤堕儴 -->
        <FaMixedMenu v-if="isTopLeftMenu" :list="menuList" />
      </div>

      <div id="app-header-toolbar" class="flex items-center gap-2.5">
        <!-- 鎼滅储 -->
        <div
          v-if="shouldShowGlobalSearch"
          class="flex items-center justify-between w-40 h-9 px-2.5 cursor-pointer border border-g-400 rounded-custom-sm max-md:hidden! transition duration-300 hover:-translate-y-0.5 hover:shadow-md"
          @click="openSearchDialog"
        >
          <div class="flex items-center">
            <FaSvgIcon icon="ri:search-line" class="text-sm text-g-500" />
            <span class="ml-1 text-xs font-normal text-g-500">{{ $t("topBar.search.title") }}</span>
          </div>
          <div class="flex items-center h-5 px-1.5 text-g-500/80 border border-g-400 rounded">
            <FaSvgIcon v-if="isWindows" icon="vaadin:ctrl-a" class="text-sm" />
            <FaSvgIcon v-else icon="ri:command-fill" class="text-xs" />
            <span class="ml-0.5 text-xs">k</span>
          </div>
        </div>

        <!-- 鍏ㄥ睆鎸夐挳 -->
        <FaIconButton
          v-if="shouldShowFullscreen"
          :icon="isFullscreen ? 'ri:fullscreen-exit-line' : 'ri:fullscreen-fill'"
          :class="[!isFullscreen ? 'full-screen-btn' : 'exit-full-screen-btn', 'ml-3']"
          class="max-md:hidden!"
          @click="toggleFullScreen"
        />

        <!-- 缁勪欢灏哄 default/large/small锛堟部鐢ㄦ棫鐗堟寔涔呭寲寮€鍏?showSizeSelect锛?-->
        <div
          v-if="shouldShowSizeSelect"
          class="flex items-center justify-center ml-1 max-md:hidden!"
        >
          <FaSizeSelect />
        </div>

        <!-- 鍥介檯鍖栨寜閽?-->
        <ElDropdown
          @command="changeLanguage"
          popper-class="langDropDownStyle"
          v-if="shouldShowLanguage"
        >
          <FaIconButton icon="ri:translate-2" class="language-btn text-[19px]" />
          <template #dropdown>
            <ElDropdownMenu>
              <div v-for="item in languageOptions" :key="item.value" class="lang-btn-item">
                <ElDropdownItem
                  :command="item.value"
                  :class="{ 'is-selected': locale === item.value }"
                >
                  <span class="menu-txt">{{ item.label }}</span>
                  <FaSvgIcon icon="ri:check-fill" v-if="locale === item.value" />
                </ElDropdownItem>
              </div>
            </ElDropdownMenu>
          </template>
        </ElDropdown>

        <!-- 璁剧疆鎸夐挳 -->
        <div v-if="shouldShowSettings">
          <ElPopover :visible="showSettingGuide" placement="bottom-start" :width="190" :offset="0">
            <template #reference>
              <div class="flex items-center justify-center">
                <FaIconButton icon="ri:settings-line" class="setting-btn" @click="openSetting" />
              </div>
            </template>
            <template #default>
              <p>
                {{ $t("topBar.guide.title") }}
                <span :style="{ color: systemThemeColor }">{{ $t("topBar.guide.theme") }}</span>
                銆?                <span :style="{ color: systemThemeColor }">{{ $t("topBar.guide.menu") }}</span>
                {{ $t("topBar.guide.description") }}
              </p>
            </template>
          </ElPopover>
        </div>

        <!-- 涓婚鍒囨崲鎸夐挳 -->
        <FaIconButton
          v-if="shouldShowThemeToggle"
          @click="themeAnimation"
          :icon="isDark ? 'ri:sun-fill' : 'ri:moon-line'"
        />

        <!-- 鐢ㄦ埛澶村儚銆佽彍鍗?-->
        <FaUserMenu />
      </div>
    </div>

    <!-- 鏍囩椤?-->
    <FaWorkTab />
  </div>
</template>

<script setup lang="ts">
import { useI18n } from "vue-i18n";
import { useRouter } from "vue-router";
import { useFullscreen, useWindowSize } from "@vueuse/core";
import { LanguageEnum, MenuTypeEnum } from "@/enums/appEnum";
import { useSettingsStore, useMenuStore, useUserStore, useConfigStore } from "@stores";
import AppConfig from "@/config";
import { languageOptions } from "@/locales";
import { mittBus, themeAnimation } from "@utils";
import { useCommon } from "@/hooks/core/useCommon";
import { useHeaderBar } from "@/hooks/core/useHeaderBar";
import FaUserMenu from "./widgets/FaUserMenu.vue";

defineOptions({ name: "FaHeaderBar" });

const isWindows = navigator.userAgent.includes("Windows");

const router = useRouter();
const { locale } = useI18n();
const { width } = useWindowSize();

const settingStore = useSettingsStore();
const userStore = useUserStore();
const menuStore = useMenuStore();
const configStore = useConfigStore();

/** 公司展示配置：底座兼容键 tenant_logo / tenant_name */
const headerLogoSrc = computed(() => {
  const raw = configStore.configData.tenant_logo?.config_value;
  return typeof raw === "string" && raw.trim() ? raw.trim() : undefined;
});

const headerSystemName = computed(() => {
  const raw = configStore.configData.tenant_name?.config_value;
  if (typeof raw === "string" && raw.trim()) return raw.trim();
  return AppConfig.systemInfo.name;
});

const {
  shouldShowMenuButton,
  shouldShowRefreshButton,
  shouldShowFastEnter,
  shouldShowBreadcrumb,
  shouldShowGlobalSearch,
  shouldShowFullscreen,
  shouldShowLanguage,
  shouldShowSettings,
  shouldShowThemeToggle,
  shouldShowSizeSelect,
  fastEnterMinWidth: headerBarFastEnterMinWidth,
} = useHeaderBar();

const { menuOpen, systemThemeColor, showSettingGuide, menuType, isDark, tabStyle, showAppLogo } =
  storeToRefs(settingStore);

const { language } = storeToRefs(userStore);
const { menuList } = storeToRefs(menuStore);


// 鑿滃崟绫诲瀷鍒ゆ柇
const isLeftMenu = computed(() => menuType.value === MenuTypeEnum.LEFT);
const isDualMenu = computed(() => menuType.value === MenuTypeEnum.DUAL_MENU);
const isTopMenu = computed(() => menuType.value === MenuTypeEnum.TOP);
const isTopLeftMenu = computed(() => menuType.value === MenuTypeEnum.TOP_LEFT);

const { isFullscreen, toggle: toggleFullscreen } = useFullscreen();

onMounted(() => {
  initLanguage();
});

/**
 * 鍒囨崲鍏ㄥ睆鐘舵€? */
const toggleFullScreen = (): void => {
  toggleFullscreen();
};

/**
 * 鍒囨崲鑿滃崟鏄剧ず/闅愯棌鐘舵€? */
const visibleMenu = (): void => {
  settingStore.setMenuOpen(!menuOpen.value);
};

const { homePath } = useCommon();
const { refresh } = useCommon();

/**
 * 璺宠浆鍒伴椤? */
const toHome = (): void => {
  router.push(homePath.value);
};

/**
 * 鍒锋柊椤甸潰
 * @param {number} time - 寤惰繜鏃堕棿锛岄粯璁や负0姣
 */
const reload = (time: number = 0): void => {
  setTimeout(() => {
    refresh();
  }, time);
};

/**
 * 鍒濆鍖栬瑷€璁剧疆
 */
const initLanguage = (): void => {
  locale.value = language.value;
};

/**
 * 鍒囨崲绯荤粺璇█
 * @param {LanguageEnum} lang - 鐩爣璇█绫诲瀷
 */
const changeLanguage = (lang: LanguageEnum): void => {
  if (locale.value === lang) return;
  locale.value = lang;
  userStore.setLanguage(lang);
  reload(50);
};

/**
 * 鎵撳紑璁剧疆闈㈡澘
 */
const openSetting = (): void => {
  mittBus.emit("openSetting");

  // 闅愯棌璁剧疆寮曞鎻愮ず
  if (showSettingGuide.value) {
    settingStore.hideSettingGuide();
  }
};

/**
 * 鎵撳紑鍏ㄥ眬鎼滅储瀵硅瘽妗? */
const openSearchDialog = (): void => {
  mittBus.emit("openSearchDialog");
};


</script>

<style lang="scss" scoped>
/* Custom animations */
@keyframes rotate180 {
  0% {
    transform: rotate(0);
  }

  100% {
    transform: rotate(180deg);
  }
}

@keyframes shake {
  0% {
    transform: rotate(0);
  }

  25% {
    transform: rotate(-5deg);
  }

  50% {
    transform: rotate(5deg);
  }

  75% {
    transform: rotate(-5deg);
  }

  100% {
    transform: rotate(0);
  }
}

@keyframes expand {
  0% {
    transform: scale(1);
  }

  50% {
    transform: scale(1.1);
  }

  100% {
    transform: scale(1);
  }
}

@keyframes shrink {
  0% {
    transform: scale(1);
  }

  50% {
    transform: scale(0.9);
  }

  100% {
    transform: scale(1);
  }
}

@keyframes moveUp {
  0% {
    transform: translateY(0);
  }

  50% {
    transform: translateY(-3px);
  }

  100% {
    transform: translateY(0);
  }
}

@keyframes breathing {
  0% {
    opacity: 0.4;
    transform: scale(0.9);
  }

  50% {
    opacity: 1;
    transform: scale(1.1);
  }

  100% {
    opacity: 0.4;
    transform: scale(0.9);
  }
}

/* Hover animation classes */
.refresh-btn:hover :deep(.fa-svg-icon) {
  animation: rotate180 0.5s;
}

.language-btn:hover :deep(.fa-svg-icon) {
  animation: moveUp 0.4s;
}

.setting-btn:hover :deep(.fa-svg-icon) {
  animation: rotate180 0.5s;
}

.full-screen-btn:hover :deep(.fa-svg-icon) {
  animation: expand 0.6s forwards;
}

:deep(.size-select-btn:hover .fa-svg-icon) {
  animation: expand 0.6s forwards;
}

.exit-full-screen-btn:hover :deep(.fa-svg-icon) {
  animation: shrink 0.6s forwards;
}




/* iPad breakpoint adjustments */
@media screen and (width <= 768px) {
  .logo2 {
    display: block !important;
  }
}

@media screen and (width <= 640px) {
  .btn-box {
    width: 40px;
  }
}
</style>
