<script setup lang="ts">
/**
 * CM-SEL-01 下拉選單顯示列
 * 狀態：未選（請選擇）／已選（主色框線）／停用（請先選上一項）
 */
import { computed, useId } from 'vue'
import AppIcon from '@/components/AppIcon.vue'

const uid = useId()

const props = withDefaults(defineProps<{ label: string; value?: string; disabled?: boolean }>(), {
  value: '',
  disabled: false,
})
const emit = defineEmits<{ open: [event: MouseEvent] }>()

const state = computed(() => (props.disabled ? 'disabled' : props.value ? 'selected' : 'empty'))
const text = computed(() => (props.disabled ? '請先選上一項' : props.value || '請選擇'))
</script>

<template>
  <div class="cm-sel-01" :class="state">
    <span :id="`${uid}-label`" class="label font-h3-semibold">{{ label }}</span>
    <button
      type="button"
      class="box font-h3-regular"
      :disabled="disabled"
      aria-haspopup="dialog"
      :aria-labelledby="`${uid}-label ${uid}-value`"
      @click="emit('open', $event)"
    >
      <span :id="`${uid}-value`" class="value">{{ text }}</span>
      <AppIcon name="chevron-down" />
    </button>
  </div>
</template>

<style scoped>
.cm-sel-01 {
  width: 100%;
  display: flex;
  flex-direction: column;
  gap: 6px;
}
.label {
  color: var(--text-primary);
}
.box {
  width: 100%;
  min-height: 48px;
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 8px;
  padding: 14px 12px 14px 16px;
  border-radius: 8px;
  background: var(--color-grey-50);
  border: 1px solid transparent;
  color: var(--text-direction);
  text-align: left;
}
.selected .box {
  border-color: var(--color-primary-500);
  color: var(--text-primary);
}
.empty .box {
  color: var(--text-direction);
}
.disabled .label {
  color: var(--text-direction);
}
.disabled .box {
  background: var(--disable-color);
  color: var(--text-direction);
}
.box :deep(svg) {
  flex: 0 0 auto;
  color: var(--text-second);
}
</style>
