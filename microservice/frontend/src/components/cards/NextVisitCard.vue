<script setup lang="ts">
/**
 * CM-CRD-03 下次回診卡
 * 註：點擊後的「回診詳情」頁尚未建檔（ID 待定），目前不設點擊行為。
 */
import { computed } from 'vue'
import type { Appointment } from '@/types'
import { formatMonthDayWeek } from '@/utils/date'

const props = withDefaults(defineProps<{ appointment: Appointment; viewer?: 'elder' | 'family' }>(), {
  viewer: 'elder',
})

const label = computed(() => (props.viewer === 'family' ? '長輩的下次回診' : '下次回診'))
</script>

<template>
  <section class="cm-crd-03" :aria-label="label">
    <span class="label font-h3-semibold">{{ label }}</span>
    <span class="datetime font-h2-semibold">{{ formatMonthDayWeek(appointment.date) }}{{ appointment.time }}</span>
    <span class="detail font-h3-regular">
      {{ appointment.hospital }}｜{{ appointment.department }}｜{{ appointment.doctor }}
    </span>
  </section>
</template>

<style scoped>
.cm-crd-03 {
  width: 100%;
  display: flex;
  flex-direction: column;
  gap: 4px;
  padding: 16px;
  border-radius: 12px;
  border: 1px solid var(--color-grey-200);
  background: var(--background-color);
}
.label {
  color: var(--text-second);
}
.datetime,
.detail {
  color: var(--text-primary);
}
</style>
