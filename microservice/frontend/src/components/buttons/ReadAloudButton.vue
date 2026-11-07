<script setup lang="ts">
/**
 * CM-BTN-01 朗讀按鈕
 * 變體：full（整區朗讀：喇叭＋文字，預設「唸給我聽」）／single（單顆朗讀：僅圖示，label 為朗讀標籤）
 */
import AppIcon from '@/components/AppIcon.vue'

withDefaults(defineProps<{ variant?: 'full' | 'single'; label?: string; flex?: boolean }>(), {
  variant: 'full',
  label: '唸給我聽',
  flex: false,
})
const emit = defineEmits<{ click: [] }>()
</script>

<template>
  <button
    v-if="variant === 'full'"
    type="button"
    class="cm-btn-01 full"
    :class="{ flex }"
    @click.stop="emit('click')"
  >
    <AppIcon name="speaker" />
    <span class="font-h3-semibold">{{ label }}</span>
  </button>
  <button v-else type="button" class="cm-btn-01 single" :aria-label="label" @click.stop="emit('click')">
    <AppIcon name="speaker" />
  </button>
</template>

<style scoped>
.cm-btn-01 {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  color: var(--color-primary-700);
}
.full {
  width: 220px;
  max-width: 100%;
  min-height: 56px;
  gap: 8px;
  padding: 0 16px;
  border-radius: 8px;
  border: 1px solid var(--color-primary-700);
  background: var(--background-color);
}
.full.flex {
  width: auto;
  flex: 1 1 0;
}
.single {
  flex: 0 0 48px;
  width: 48px;
  height: 48px;
  border-radius: 24px;
  background: var(--color-primary-50);
}
</style>
