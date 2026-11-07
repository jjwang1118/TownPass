<script setup lang="ts">
/**
 * 長者：手動新增藥品「已輸入」確認（彈窗）
 * 自行設計（非 Figma 原稿），風格比照 EL-MD-01
 * - 列出目前已輸入的所有藥品
 * - 「確認」→ EL-PG-07 確認藥單；「再加一個藥」→ 關閉彈窗，清空表單繼續輸入
 */
import { ref, toRef, useId } from 'vue'
import { useOverlay } from '@/composables/useOverlay'
import { amountText, slotNames } from '@/utils/schedule'
import type { MedicineFormValue } from '@/types'

const props = defineProps<{ open: boolean; medicines: MedicineFormValue[] }>()
const emit = defineEmits<{ close: []; confirm: []; more: [] }>()

const panel = ref<HTMLElement | null>(null)
const titleId = useId()
const descId = useId()
useOverlay(toRef(props, 'open'), panel, () => emit('close'))

const detail = (m: MedicineFormValue) => [amountText(m.amount), slotNames(m.slots), m.meal].join('｜')
</script>

<template>
  <Teleport to="body">
    <div v-if="open && medicines.length" class="medicine-added">
      <div class="mask" aria-hidden="true" @click="emit('close')" />
      <div
        ref="panel"
        class="dialog"
        role="dialog"
        aria-modal="true"
        :aria-labelledby="titleId"
        :aria-describedby="descId"
      >
        <div class="head">
          <svg width="32" height="32" viewBox="0 0 32 32" aria-hidden="true" focusable="false">
            <circle cx="16" cy="16" r="16" fill="#5AB4C5" />
            <path d="M9.5 16.5l4.5 4.5 8.5-9" fill="none" stroke="#FFFFFF" stroke-width="3" stroke-linecap="round" stroke-linejoin="round" />
          </svg>
          <h2 :id="titleId" class="title font-h2-semibold">
            已輸入<span v-if="medicines.length > 1"> {{ medicines.length }} 個藥</span>
          </h2>
        </div>
        <ul :id="descId" class="list">
          <li v-for="(m, i) in medicines" :key="`${m.name}-${i}`" class="summary">
            <p class="name font-h3-semibold">{{ m.name }}</p>
            <p class="detail font-h3-regular">{{ detail(m) }}</p>
          </li>
        </ul>
        <button type="button" class="btn primary font-h3-regular" data-autofocus @click="emit('confirm')">確認</button>
        <button type="button" class="btn secondary font-h3-regular" @click="emit('more')">再加一個藥</button>
      </div>
    </div>
  </Teleport>
</template>

<style scoped>
.medicine-added {
  position: fixed;
  inset: 0;
  z-index: 100;
  display: flex;
  align-items: center;
  justify-content: center;
  padding: 16px;
}
.mask {
  position: absolute;
  inset: 0;
  background: var(--overlay);
}
.dialog {
  position: relative;
  width: 311px;
  max-width: 100%;
  max-height: 90dvh;
  overflow-y: auto;
  display: flex;
  flex-direction: column;
  gap: 16px;
  padding: 24px;
  border-radius: 16px;
  background: var(--background-color);
}
.head {
  display: flex;
  align-items: center;
  gap: 12px;
}
.title {
  color: var(--text-primary);
}
.list {
  list-style: none;
  margin: 0;
  padding: 0;
  display: flex;
  flex-direction: column;
  gap: 8px;
}
.summary {
  display: flex;
  flex-direction: column;
  gap: 4px;
  padding: 12px 16px;
  border-radius: 12px;
  background: var(--color-primary-50);
}
.name {
  color: var(--text-primary);
  overflow-wrap: anywhere;
}
.detail {
  color: var(--text-second);
}
.btn {
  width: 100%;
  min-height: 56px;
  border-radius: 10px;
}
.primary {
  background: var(--color-primary-500);
  color: var(--color-white);
}
.secondary {
  margin-top: -4px;
  background: var(--background-color);
  color: var(--color-primary-500);
  border: 1px solid var(--color-primary-500);
}
</style>
