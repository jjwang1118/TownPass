<script setup lang="ts">
/** CM-CRD-04 功能入口列（圖示＋標題＋副標＋展開箭頭） */
import AppIcon, { type IconName } from '@/components/AppIcon.vue'

defineProps<{ icon: IconName; title: string; subtitle: string }>()
const emit = defineEmits<{ click: [] }>()
</script>

<template>
  <button type="button" class="cm-crd-04" @click="emit('click')">
    <span class="icon"><AppIcon :name="icon" /></span>
    <span class="texts">
      <span class="title font-h3-semibold">{{ title }}</span>
      <span class="subtitle font-h3-regular">{{ subtitle }}</span>
    </span>
    <AppIcon name="chevron-right" class="arrow" />
  </button>
</template>

<style scoped>
.cm-crd-04 {
  width: 100%;
  min-height: 48px;
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 16px;
  border-radius: 12px;
  border: 1px solid var(--color-grey-200);
  background: var(--background-color);
  text-align: left;
}
.icon {
  flex: 0 0 48px;
  width: 48px;
  height: 48px;
  border-radius: 24px;
  background: var(--color-primary-50);
  color: var(--color-primary-700);
  display: flex;
  align-items: center;
  justify-content: center;
}
.texts {
  flex: 1 1 auto;
  min-width: 0;
  display: flex;
  flex-direction: column;
  gap: 2px;
}
.title {
  color: var(--text-primary);
}
.subtitle {
  color: var(--text-second);
}
.arrow {
  flex: 0 0 24px;
  color: var(--text-second);
}
</style>
