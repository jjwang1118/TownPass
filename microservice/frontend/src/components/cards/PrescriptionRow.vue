<script setup lang="ts">
/** EL-CRD-14 藥單列（吃藥中／已吃完），點擊整列 → 藥單詳情 */
import AppIcon from '@/components/AppIcon.vue'
import RxBadge from './RxBadge.vue'

defineProps<{ code: string; hospital: string; department: string; statusText: string; finished: boolean }>()
const emit = defineEmits<{ click: [] }>()
</script>

<template>
  <button type="button" class="el-crd-14" :class="{ finished }" @click="emit('click')">
    <RxBadge :code="code" :finished="finished" :label="finished ? '已吃完的藥單' : `藥單 ${code}`" />
    <span class="texts">
      <span class="line1 font-h3-semibold">{{ department ? `${hospital}｜${department}` : hospital }}</span>
      <span class="line2 font-h3-regular">{{ statusText }}</span>
    </span>
    <AppIcon name="chevron-right" class="arrow" />
  </button>
</template>

<style scoped>
.el-crd-14 {
  width: 100%;
  min-height: 48px;
  text-align: left;
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 16px;
  border-radius: 12px;
  border: 1px solid var(--color-grey-200);
  background: var(--background-color);
}
.texts {
  flex: 1 1 auto;
  min-width: 0;
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
.arrow {
  flex: 0 0 24px;
  color: var(--text-second);
}
.finished {
  background: var(--color-grey-50);
}
.finished .line1 {
  color: var(--text-second);
}
</style>
