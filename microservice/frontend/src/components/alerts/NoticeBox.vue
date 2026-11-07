<script setup lang="ts">
/**
 * 提示框共用骨架：
 * - info → CM-ALT-01 提示框（藍綠）
 * - warning → CM-ALT-03 提醒框（橘）
 * - severe → FM-ALT-01 提醒框（嚴重警示，白底紅框）
 */
import AppIcon from '@/components/AppIcon.vue'

withDefaults(defineProps<{ variant?: 'info' | 'warning' | 'severe'; live?: boolean }>(), {
  variant: 'info',
  live: false,
})
</script>

<template>
  <div class="notice" :class="variant" :role="live ? 'status' : undefined">
    <span class="icon">
      <AppIcon :name="variant === 'info' ? 'info' : 'warning'" />
    </span>
    <p class="text font-h3-regular"><slot /></p>
  </div>
</template>

<style scoped>
.notice {
  width: 100%;
  display: flex;
  align-items: flex-start;
  gap: 12px;
  padding: 12px 16px;
  border-radius: 8px;
  text-align: left;
}
.icon {
  flex: 0 0 24px;
  display: flex;
}
.text {
  flex: 1 1 auto;
  color: var(--text-primary);
}
.info {
  background: var(--color-primary-50);
  border: 1px solid var(--color-primary-300);
}
.info .icon {
  color: var(--color-primary-700);
}
.warning {
  background: var(--color-secondary-50);
  border: 1px solid var(--reminder-orange-500);
}
.warning .icon {
  color: var(--reminder-orange-500);
}
.severe {
  background: var(--background-color);
  border: 2px solid var(--alarm-red-500);
}
.severe .icon {
  color: var(--alarm-red-500);
}
</style>
