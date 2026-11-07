<script setup lang="ts">
/** CM-CRD-06 緊急醫療卡本體（長者／家屬共用，純展示） */
import { computed } from 'vue'
import InfoRow from './InfoRow.vue'
import type { EmergencyCard, Medicine } from '@/types'
import { cardSummary, contactText, listText } from '@/utils/card'

const props = withDefaults(
  defineProps<{ card: EmergencyCard; medicines: Medicine[]; viewer?: 'elder' | 'family' }>(),
  { viewer: 'elder' },
)

const source = computed(() => (props.viewer === 'family' ? '（來自長輩的藥單）' : '（來自您的藥單）'))
const summary = computed(() => cardSummary(props.card, new Date()))

const topRows = computed(() => {
  const rows = [{ label: '緊急聯絡人', value: contactText(props.card.contact1) }]
  if (props.card.contact2) rows.push({ label: '第二聯絡人', value: contactText(props.card.contact2) })
  rows.push(
    { label: '慢性病', value: listText(props.card.chronic) },
    { label: '藥物過敏', value: props.card.drugAllergy || '無' },
    { label: '食物過敏', value: props.card.foodAllergy || '無' },
  )
  return rows
})

const bottomRows = computed(() => [
  { label: '常去醫院', value: props.card.hospitalRecord.replace('｜', '｜病歷號 ') },
  { label: '特殊狀況', value: listText(props.card.special) },
  { label: '慣用語言', value: props.card.language || '未填寫' },
])
</script>

<template>
  <section class="cm-crd-06" aria-label="緊急醫療卡">
    <div class="basic">
      <span class="tag font-h3-semibold">緊急醫療卡</span>
      <span class="name font-h1-semibold">{{ card.name }}</span>
      <span class="summary font-h3-regular">{{ summary }}</span>
    </div>
    <div class="body">
      <dl class="rows">
        <InfoRow v-for="row in topRows" :key="row.label" :label="row.label" :value="row.value" />
      </dl>
      <div class="meds">
        <p class="meds-title font-h3-regular">
          <span class="text-second">目前用藥</span>
          <span class="source">{{ source }}</span>
        </p>
        <ul class="meds-list">
          <li v-for="m in medicines" :key="m.code" class="font-h3-semibold">
            {{ m.code }}　{{ m.name }}｜{{ m.effect }}
          </li>
          <li v-if="medicines.length === 0" class="font-h3-regular text-second">目前沒有用藥</li>
        </ul>
      </div>
      <dl class="rows">
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
