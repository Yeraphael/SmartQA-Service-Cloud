<!--
  布局根容器：三区域结构
    - #app-sidebar  ← 左侧菜单导航（收起/展开）
    - #app-main     ← 右侧主区域（顶栏 + 页面内容）
      - #app-header  顶栏（面包屑、搜索、通知、用户菜单）
      - #app-content 页面内容（RouterView + 页签）
    - #app-global   ← 全局浮层层（Toast、Modal、新手引导）
-->
<template>
  <div class="app-layout">
    <!-- 左侧菜单导航 -->
    <aside id="app-sidebar">
      <FaSidebarMenu />
    </aside>

    <!-- 右侧主区域 -->
    <main id="app-main">
      <div id="app-header">
        <FaHeaderBar />
      </div>
      <div id="app-content">
        <FaPageContent />
      </div>
    </main>

    <!-- 全局浮层层（通知等跨页面组件） -->
  </div>
</template>

<script setup lang="ts">
/**
 * 布局根组件 —— 组装侧栏、顶栏、页面内容、全局浮层。
 */
defineOptions({ name: "AppLayout" });
</script>

<style lang="scss" scoped>
@use "./fa-layouts";
</style>
