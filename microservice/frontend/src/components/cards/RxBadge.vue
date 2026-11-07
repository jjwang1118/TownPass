<script setup lang="ts">
/**
 * 藥單徽章（64×48、圓角 24）
 * 色系依藥單字母：A、C、E…→ Primary/700 白字；B、D、F…→ Secondary/500 深字；已吃完 → Grey/500 白字
 */
import { computed } from 'vue'

const props = withDefaults(defineProps<{ code: string; finished?: boolean; label?: string }>(), {
  finished: false,
})

const tone = computed(() => {
  if (props.finished) return 'grey'
  const letter = props.code.charCodeAt(0) - 65
  return letter % 2 === 0 ? 'primary' : 'secondary'
})
</script>

<template>
  <span class="rx-badge font-h2-semibold" :class="tone" :aria-label="label">{{ finished ? '舊' : code }}</span>
</template>

<style scoped>
.rx-badge {
  flex: 0 0 auto;
  min-width: 64px;
  height: 48px;
  padding: 0 14px;
  border-radius: 24px;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  white-space: nowrap;
}
.primary {
  background: var(--color-primary-700);
  color: var(--color-white);
}
.secondary {
  background: var(--color-secondary-500);
  color: var(--text-primary);
}
.grey {
  background: var(--color-grey-500);
  color: var(--color-white);
}
</style>
