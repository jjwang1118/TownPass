<script setup lang="ts">
/** CM-NAV-02 導覽列（返回＋標題） */
import AppIcon from '@/components/AppIcon.vue'

defineProps<{ title: string }>()
const emit = defineEmits<{ back: [] }>()
</script>

<template>
  <header class="cm-nav-02">
    <button type="button" class="back" aria-label="返回上一頁" @click="emit('back')">
      <AppIcon name="back" />
    </button>
    <h1 class="title font-h3-semibold">{{ title }}</h1>
    <span class="placeholder" aria-hidden="true" />
  </header>
</template>

<style scoped>
.cm-nav-02 {
  position: sticky;
  top: 0;
  z-index: 10;
  min-height: var(--nav-height);
  display: flex;
  align-items: center;
  background: var(--background-color);
}
.back,
.placeholder {
  flex: 0 0 56px;
  width: 56px;
  height: 56px;
  display: flex;
  align-items: center;
  justify-content: center;
  color: var(--text-second);
}
.title {
  flex: 1 1 auto;
  text-align: center;
  color: var(--text-second);
}
</style>
