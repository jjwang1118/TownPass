<script setup lang="ts">
/** EL-CRD-12 邀請碼卡片（6 碼數字，3+3 分組顯示） */
import { computed } from 'vue'

const props = defineProps<{ code: string; validText: string }>()
const grouped = computed(() => `${props.code.slice(0, 3)} ${props.code.slice(3)}`)
</script>

<template>
  <section class="el-crd-12" aria-label="邀請碼">
    <p class="code font-h1-semibold" :aria-label="code.split('').join(' ')">{{ grouped }}</p>
    <p class="valid font-h3-regular" aria-live="polite">{{ validText }}</p>
  </section>
</template>

<style scoped>
.el-crd-12 {
  width: 100%;
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 8px;
  padding: 24px 16px;
  border-radius: 12px;
  background: var(--color-primary-50);
}
.code {
  color: var(--color-primary-700);
  letter-spacing: 0.1em;
  font-variant-numeric: tabular-nums;
}
.valid {
  color: var(--text-second);
}
</style>
