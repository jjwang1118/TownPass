<script setup lang="ts">
/** RE-BTN-01 緊急撥號按鈕（TownPass 48/Button Alarm） */
import AppIcon from '@/components/AppIcon.vue'

const emit = defineEmits<{ click: [] }>()
</script>

<template>
  <button type="button" class="re-btn-01 font-h3-regular" @click="emit('click')">
    <AppIcon name="phone" :size="20" />
    <slot />
  </button>
</template>

<style scoped>
.re-btn-01 {
  width: 100%;
  min-height: 56px;
  padding: 8px 16px;
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 8px;
  border-radius: 10px;
  background: var(--alarm-red-500);
  color: var(--color-white);
}
</style>
