<script setup lang="ts">
/**
 * CM-CRD-06 緊急醫療卡本體（長者／家屬共用，純展示）
 * 只顯示有填寫的欄位；目前用藥有藥時才顯示
 */
import { computed } from 'vue'
import InfoRow from './InfoRow.vue'
import type { EmergencyCard, Medicine } from '@/types'
import { cardRows, cardSummary } from '@/utils/card'

const props = withDefaults(
  defineProps<{ card: EmergencyCard; medicines: Medicine[]; viewer?: 'elder' | 'family' }>(),
  { viewer: 'elder' },
)

const source = computed(() => (props.viewer === 'family' ? '（來自長輩的藥單）' : '（來自您的藥單）'))
const summary = computed(() => cardSummary(props.card, new Date()))
const rows = computed(() => cardRows(props.card))
const topRows = computed(() => rows.value.top)
const bottomRows = computed(() => rows.value.bottom)
const hasBody = computed(() => topRows.value.length > 0 || bottomRows.value.length > 0 || props.medicines.length > 0)
</script>

<template>
  <section class="cm-crd-06" aria-label="緊急醫療卡">
    <div class="basic">
      <span class="tag font-h3-semibold">緊急醫療卡</span>
      <span v-if="card.name" class="name font-h1-semibold">{{ card.name }}</span>
      <span v-if="summary" class="summary font-h3-regular">{{ summary }}</span>
    </div>
    <div v-if="hasBody" class="body">
      <dl v-if="topRows.length" class="rows">
        <InfoRow
          v-for="(row, i) in topRows"
          :key="row.label"
          :label="row.label"
          :value="row.value"
          :show-divider="i < topRows.length - 1 || medicines.length > 0 || bottomRows.length > 0"
        />
      </dl>
      <div v-if="medicines.length" class="meds" :class="{ last: bottomRows.length === 0 }">
        <p class="meds-title font-h3-regular">
          <span class="text-second">目前用藥</span>
          <span class="source">{{ source }}</span>
        </p>
        <ul class="meds-list">
          <li v-for="m in medicines" :key="m.code" class="font-h3-semibold">
            {{ m.code }}　{{ m.name }}｜{{ m.effect }}
          </li>
        </ul>
      </div>
      <dl v-if="bottomRows.length" class="rows">
        <InfoRow
          v-for="(row, i) in bottomRows"
          :key="row.label"
          :label="row.label"
          :value="row.value"
          :show-divider="i < bottomRows.length - 1"
        />
      </dl>
    </div>
  </section>
</template>

<style scoped>
.cm-crd-06 {
  width: 100%;
  border-radius: 12px;
  border: 2px solid var(--alarm-red-500);
  overflow: hidden;
}
.basic {
  display: flex;
  flex-direction: column;
  gap: 4px;
  padding: 16px;
  background: var(--alarm-red-500);
  color: var(--color-white);
}
.body {
  padding: 0 16px;
  background: var(--background-color);
}
.rows {
  margin: 0;
}
.meds {
  padding: 12px 0;
  border-bottom: 1px solid var(--color-grey-100);
}
.meds.last {
  border-bottom: none;
}
.meds-title {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
}
.source {
  color: var(--color-primary-700);
}
.meds-list {
  list-style: none;
  margin: 8px 0 0;
  padding: 0;
  display: flex;
  flex-direction: column;
  gap: 4px;
  color: var(--text-primary);
}
</style>
