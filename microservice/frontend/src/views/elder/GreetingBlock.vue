<script setup lang="ts">
/** 首頁問候區（EL-PG-01／EL-PG-02 共用，純文字） */
import { state } from '@/store'
import { formatClock, formatLongDate, greeting } from '@/utils/date'

defineProps<{ now: Date }>()
</script>

<template>
  <section class="greeting">
    <p class="hello font-h2-semibold">{{ state.elder.name }}，{{ greeting(now) }}</p>
    <p class="date font-h3-regular">{{ formatLongDate(now) }}{{ formatClock(now) }}</p>
  </section>
</template>

<style scoped>
.greeting {
  display: flex;
  flex-direction: column;
  gap: 4px;
}
.hello {
  color: var(--text-primary);
}
.date {
  color: var(--text-second);
}
</style>
