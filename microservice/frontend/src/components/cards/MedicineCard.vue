<script setup lang="ts">
/**
 * CM-CRD-01 藥品卡
 * - showDepartment：EL-PG-01 顯示「科別｜功效｜時機」；EL-PG-03／FM-PG-04 只顯示「功效｜時機」
 * - clickable：長者可點整列；家屬視角不可點
 * - 單顆朗讀不冒泡至整列
 */
import { computed } from 'vue'
import ReadAloudButton from '@/components/buttons/ReadAloudButton.vue'
import RxBadge from './RxBadge.vue'
import { amountText, slotNames } from '@/utils/schedule'
import type { Medicine } from '@/types'

const props = withDefaults(
  defineProps<{
    medicine: Medicine
    department?: string
    showDepartment?: boolean
    /** 顯示服用時段（藥單詳情用：早上、晚上） */
    showSlots?: boolean
    /** 額外說明列（藥單詳情用：剩 26 顆，約 26 天） */
    note?: string
    clickable?: boolean
  }>(),
  { showDepartment: false, showSlots: false, clickable: true },
)
const emit = defineEmits<{ click: []; speak: [] }>()

const meta = computed(() =>
  [
    props.showDepartment ? props.department : '',
    props.medicine.effect,
    props.showSlots ? slotNames(props.medicine.slots) : '',
    props.medicine.meal,
  ]
    .filter(Boolean)
    .join('｜'),
)
</script>

<template>
  <article class="cm-crd-01">
    <component
      :is="clickable ? 'button' : 'div'"
      :type="clickable ? 'button' : undefined"
      class="main"
      @click="clickable && emit('click')"
    >
      <span class="top">
        <RxBadge :code="medicine.code" />
        <span class="amount font-h2-semibold">{{ amountText(medicine.amount) }}</span>
      </span>
      <span class="name font-h3-regular">{{ medicine.name }}</span>
      <span class="meta font-h3-regular">{{ meta }}</span>
      <span v-if="note" class="note font-h3-semibold">{{ note }}</span>
    </component>
    <ReadAloudButton variant="single" :label="`朗讀 ${medicine.code} ${medicine.name}`" @click="emit('speak')" />
  </article>
</template>

<style scoped>
.cm-crd-01 {
  width: 100%;
  display: flex;
  align-items: flex-start;
  gap: 8px;
  padding: 16px;
  border-radius: 12px;
  border: 1px solid var(--color-grey-200);
  background: var(--background-color);
}
.main {
  flex: 1 1 auto;
  min-width: 0;
  display: flex;
  flex-direction: column;
  gap: 2px;
  text-align: left;
  background: transparent;
}
.top {
  display: flex;
  align-items: center;
  gap: 12px;
  margin-bottom: 6px;
}
.amount,
.name {
  color: var(--text-primary);
}
.meta {
  color: var(--text-second);
}
.note {
  margin-top: 4px;
  color: var(--color-primary-700);
}
</style>
