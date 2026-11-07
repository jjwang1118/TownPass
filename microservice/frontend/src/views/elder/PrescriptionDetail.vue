<script setup lang="ts">
/**
 * 長者：藥單詳情（EL-PG-18 規格中「ID 待定」的頁面，依「顯示此藥單所有藥品清單」自行設計）
 * 從「我的藥單」點任一藥單列進入
 */
import { computed, onMounted } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import PageLayout from '@/components/PageLayout.vue'
import PrescriptionHeader from '@/components/cards/PrescriptionHeader.vue'
import MedicineCard from '@/components/cards/MedicineCard.vue'
import LanguageSwitch from '@/components/segments/LanguageSwitch.vue'
import InfoNotice from '@/components/alerts/InfoNotice.vue'
import { daysLeft, isFinished, state } from '@/store'
import { useTts } from '@/composables/useTts'
import { medicineSpeech } from '@/utils/speech'
import { medicineDaysLeft, pillsLeft, prescriptionSupplyDays } from '@/utils/supply'
import type { Medicine } from '@/types'

const route = useRoute()
const router = useRouter()
const { speak } = useTts()
const now = new Date()

const rx = computed(() => state.prescriptions[Number(route.params.index)])
const finished = computed(() => (rx.value ? isFinished(rx.value, now) : false))
const statusText = computed(() => {
  if (!rx.value) return ''
  return finished.value ? '這張藥單已經吃完了' : `這張藥單還剩 ${daysLeft(rx.value, now)} 天`
})
/** 剩 26 顆，約 26 天（剩下顆數 ÷ 每天吃幾顆） */
function supplyNote(m: Medicine): string {
  if (!rx.value) return ''
  const left = pillsLeft(m, rx.value.visitDate, now)
  if (left <= 0) return `已吃完（共 ${m.quantity} 顆）`
  return `剩 ${left} 顆，約 ${medicineDaysLeft(m, rx.value.visitDate, now)} 天`
}

onMounted(() => {
  if (!rx.value) router.replace('/elder/prescriptions')
})
</script>

<template>
  <PageLayout title="藥單詳情" fallback="/elder/prescriptions">
    <template v-if="rx">
      <PrescriptionHeader
        :code="rx.code"
        :hospital="rx.hospital"
        :department="rx.department"
        :visit-date="rx.visitDate"
        :days="prescriptionSupplyDays(rx)"
      />
      <p class="status font-h3-semibold" :class="{ finished }">{{ statusText }}</p>

      <div class="read-row">
        <span class="read-label font-h3-regular">朗讀語言</span>
        <LanguageSwitch v-model="state.lang" />
      </div>

      <h2 class="section-label">這張藥單的藥（共 {{ rx.medicines.length }} 種）</h2>
      <MedicineCard
        v-for="m in rx.medicines"
        :key="m.code"
        :medicine="m"
        show-slots
        :note="supplyNote(m)"
        :clickable="false"
        @speak="speak(medicineSpeech(m, true, state.lang), state.lang)"
      />

      <InfoNotice>請以藥袋和藥師說明為準。</InfoNotice>
    </template>
  </PageLayout>
</template>

<style scoped>
.status {
  color: var(--color-primary-700);
}
.status.finished {
  color: var(--text-second);
}
.read-row {
  display: flex;
  align-items: center;
  justify-content: space-between;
  flex-wrap: wrap;
  gap: 12px;
}
</style>
