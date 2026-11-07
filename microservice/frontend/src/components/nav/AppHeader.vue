<script setup lang="ts">
/** CM-NAV-01 導覽列（logo＋呷藥囉） */
import AppLogo from '@/components/AppLogo.vue'
</script>

<template>
  <header class="cm-nav-01">
    <AppLogo :size="24" />
    <h1 class="title font-h3-semibold">呷藥囉</h1>
  </header>
</template>

<style scoped>
.cm-nav-01 {
  position: sticky;
  top: 0;
  z-index: 10;
  height: var(--nav-height);
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 8px;
  background: var(--background-color);
}
.title {
  color: var(--text-second);
}
</style>
