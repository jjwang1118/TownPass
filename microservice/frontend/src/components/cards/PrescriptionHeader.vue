<script setup lang="ts">
/** EL-CRD-08 藥單標頭 */
import RxBadge from './RxBadge.vue'
import { formatSlashDate } from '@/utils/date'

defineProps<{ code: string; hospital: string; department: string; visitDate: string; days: number }>()
</script>

<template>
  <section class="el-crd-08" :aria-label="`藥單 ${code}`">
    <RxBadge :code="code" />
    <span class="texts">
      <span class="line1 font-h3-semibold">{{ department ? `${hospital}｜${department}` : hospital }}</span>
      <span class="line2 font-h3-regular">看診 {{ formatSlashDate(visitDate) }}｜{{ days }} 天</span>
    </span>
  </section>
</template>

<style scoped>
.el-crd-08 {
  width: 100%;
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 12px 16px;
  border-radius: 12px;
  background: var(--color-grey-50);
}
.texts {
  display: flex;
  flex-direction: column;
  gap: 2px;
}
.line1 {
  color: var(--text-primary);
}
.line2 {
  color: var(--text-second);
}
</style>
