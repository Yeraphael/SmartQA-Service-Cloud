<template>
  <ElConfigProvider
    :size="size"
    :locale="locale"
    :z-index="3000"
    :card="{ shadow: 'never' }"
  >
    <RouterView />
  </ElConfigProvider>
</template>

<script setup lang="ts">
import { computed, onBeforeMount, onMounted, onUnmounted } from "vue";
import { useAppStore } from "./store";
import { ComponentSize } from "./enums/settings/layout.enum";
import { toggleTransition } from "./utils/ui";
import { initializeTheme } from "./hooks/core/useTheme";
import { useAppBootstrap } from "@/hooks/core/useAppBootstrap";
import en from "element-plus/es/locale/lang/en";
import zhCn from "element-plus/es/locale/lang/zh-cn";
import { router } from "@/router";

const appStore = useAppStore();

const size = computed(() => appStore.size as ComponentSize);
const locale = computed(() => (appStore.language === "en" ? en : zhCn));

onBeforeMount(() => {
  toggleTransition(true);
  initializeTheme();
});

const handleStorageInvalidated = () => {
  router.push({ name: "Login" });
};

const { bootstrap } = useAppBootstrap();

onMounted(() => {
  bootstrap();
  window.addEventListener("app:storage-invalidated", handleStorageInvalidated);
});

onUnmounted(() => {
  window.removeEventListener("app:storage-invalidated", handleStorageInvalidated);
});
</script>
