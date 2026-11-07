<script setup lang="ts" generic="T extends string">
/** 頁內切換（樣式同 CM-SEG-01，選項平分整列寬度）；例：邀請家屬／綁定長輩 */
defineProps<{ options: { value: T; label: string }[]; label: string }>()
const model = defineModel<T>({ required: true })
</script>

<template>
  <div class="tab-switch" role="radiogroup" :aria-label="label">
    <button
      v-for="opt in options"
      :key="opt.value"
      type="button"
      role="radio"
      :aria-checked="model === opt.value"
      class="option"
      :class="model === opt.value ? 'selected font-h3-semibold' : 'font-h3-regular'"
      @click="model = opt.value"
    >
      {{ opt.label }}
    </button>
  </div>
</template>

<style scoped>
.tab-switch {
  display: flex;
  gap: 4px;
  padding: 4px;
  border-radius: 8px;
  background: var(--color-grey-50);
}
.option {
  flex: 1;
  min-height: 48px;
  padding: 0 8px;
  border-radius: 6px;
  color: var(--text-second);
  background: transparent;
}
.option.selected {
  background: var(--background-color);
  color: var(--color-primary-700);
}
</style>
