<script setup lang="ts">
/**
 * RE-PG-03 救護人員：緊急醫療卡
 * - 開啟後 30 分鐘自動關閉 → RE-PG-04，倒數顯示於頂部提醒框
 * - 版面比長者／家屬版精簡（無外層紅框），以利現場快速閱讀
 */
import { computed, onMounted, watch } from 'vue'
import { useRouter } from 'vue-router'
import PageLayout from '@/components/PageLayout.vue'
import WarningNotice from '@/components/alerts/WarningNotice.vue'
import InfoNotice from '@/components/alerts/InfoNotice.vue'
import EmergencyCallButton from '@/components/buttons/EmergencyCallButton.vue'
import SecondaryButton from '@/components/buttons/SecondaryButton.vue'
import InfoList from '@/components/cards/InfoList.vue'
import { RESCUE_CARD_MINUTES } from '@/data/constants'
import { activeMedicines, closeRescueCard, state } from '@/store'
import { useNow } from '@/composables/useNow'
import { phoneCall } from '@/composables/flutterBridge'
import { cardSummary, listText } from '@/utils/card'
import { formatCountdown } from '@/utils/date'

const router = useRouter()
const now = useNow(1_000)

const card = computed(() => state.card)
const medicines = computed(() => activeMedicines(now.value))
const openedAt = computed(() => state.rescue?.openedAt ?? null)
const remaining = computed(() =>
  openedAt.value ? (openedAt.value + RESCUE_CARD_MINUTES * 60_000 - now.value.getTime()) / 1000 : 0,
)

const rows = computed(() => [
  { label: '慢性病', value: listText(card.value.chronic) },
  { label: '藥物過敏', value: card.value.drugAllergy || '無' },
  { label: '食物過敏', value: card.value.foodAllergy || '無' },
  { label: '特殊狀況', value: listText(card.value.special) },
  { label: '慣用語言', value: card.value.language || '未填寫' },
  { label: '最後更新', value: card.value.updatedAt },
])

// 倒數到 0 自動關閉
watch(remaining, (sec) => {
  if (openedAt.value && sec <= 0) {
    closeRescueCard()
    router.replace('/rescue/closed')
  }
})

onMounted(() => {
  if (!openedAt.value) router.replace('/rescue/search')
})

function back() {
  // 離開即關閉查詢結果，保護長者隱私
  closeRescueCard()
  router.replace('/rescue/search')
}
</script>

<template>
  <PageLayout title="緊急醫療卡" :on-back="back">
    <template v-if="openedAt">
      <WarningNotice>
        已通知家屬｜此頁 <span class="countdown">{{ formatCountdown(remaining) }}</span> 後自動關閉
      </WarningNotice>
      <InfoNotice>以下資料由長者本人提供，僅供參考，請以現場評估為準。</InfoNotice>

      <section class="basic" aria-label="基本資料">
        <p class="font-h1-semibold">{{ card.name }}</p>
        <p class="font-h3-regular">{{ cardSummary(card, now) }}</p>
      </section>

      <EmergencyCallButton @click="phoneCall(card.contact1.phone)">
        撥打 {{ card.contact1.name }}（{{ card.contact1.relation }}）
      </EmergencyCallButton>
      <SecondaryButton v-if="card.contact2" @click="phoneCall(card.contact2.phone)">
        撥打 {{ card.contact2.name }}（{{ card.contact2.relation }}）
      </SecondaryButton>

      <InfoList :rows="rows" label="醫療卡內容" />

      <section class="meds" aria-labelledby="rescue-meds-title">
        <h2 id="rescue-meds-title" class="meds-title font-h3-regular">
          <span class="text-second">目前用藥</span>
          <span class="source">（來自長者的藥單）</span>
        </h2>
        <ul class="meds-list">
          <li v-for="m in medicines" :key="m.code" class="font-h3-semibold">{{ m.name }}｜{{ m.effect }}</li>
          <li v-if="medicines.length === 0" class="font-h3-regular text-second">目前沒有用藥</li>
        </ul>
      </section>
    </template>
  </PageLayout>
</template>

<style scoped>
.countdown {
  font-weight: 700;
  font-variant-numeric: tabular-nums;
}
.basic {
  display: flex;
  flex-direction: column;
  gap: 4px;
  padding: 16px;
  border-radius: 12px;
  background: var(--alarm-red-500);
  color: var(--color-white);
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
