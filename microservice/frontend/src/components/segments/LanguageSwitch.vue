<script setup lang="ts">
/** CM-SEG-01 語言切換（國語／英文）；切換不會立即朗讀 */
import type { Lang } from '@/types'

const model = defineModel<Lang>({ required: true })
const options: { value: Lang; label: string; lang: string }[] = [
  { value: 'zh', label: '國語', lang: 'zh-TW' },
  { value: 'en', label: 'English', lang: 'en' },
]
</script>

<template>
  <div class="cm-seg-01" role="radiogroup" aria-label="朗讀語言">
    <button
      v-for="opt in options"
      :key="opt.value"
      type="button"
      role="radio"
      :aria-checked="model === opt.value"
      :lang="opt.lang"
      class="option"
      :class="model === opt.value ? 'selected font-h3-semibold' : 'font-h3-regular'"
      @click="model = opt.value"
    >
      {{ opt.label }}
    </button>
  </div>
</template>

<style scoped>
.cm-seg-01 {
  display: inline-flex;
  gap: 4px;
  padding: 4px;
  border-radius: 8px;
  background: var(--color-grey-50);
}
.option {
  min-width: 64px;
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
