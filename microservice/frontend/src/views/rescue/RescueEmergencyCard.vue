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
import { cardRows, cardSummary, hasContact, isCardEmpty } from '@/utils/card'
import { formatCountdown } from '@/utils/date'

const router = useRouter()
const now = useNow(1_000)

const card = computed(() => state.card)
const medicines = computed(() => activeMedicines(now.value))
const openedAt = computed(() => state.rescue?.openedAt ?? null)
const remaining = computed(() =>
  openedAt.value ? (openedAt.value + RESCUE_CARD_MINUTES * 60_000 - now.value.getTime()) / 1000 : 0,
)

/** 只列出長者有填寫的欄位（聯絡人另以撥號按鈕呈現） */
const rows = computed(() => {
  const { top, bottom } = cardRows(card.value)
  const list = [...top, ...bottom].filter((r) => r.label !== '緊急聯絡人' && r.label !== '第二聯絡人')
  if (card.value.updatedAt) list.push({ label: '最後更新', value: card.value.updatedAt })
  return list
})
const summary = computed(() => cardSummary(card.value, now.value))
const empty = computed(() => isCardEmpty(card.value) && medicines.value.length === 0)
const contact1 = computed(() => (hasContact(card.value.contact1) && card.value.contact1.phone ? card.value.contact1 : null))
const contact2 = computed(() => (hasContact(card.value.contact2) && card.value.contact2.phone ? card.value.contact2 : null))
const relationText = (r: string) => (r ? `（${r}）` : '')

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

      <p v-if="empty" class="empty font-h3-semibold" role="status">長者還沒有填寫緊急醫療卡，請以現場評估為準。</p>

      <section v-if="card.name || summary" class="basic" aria-label="基本資料">
        <p v-if="card.name" class="font-h1-semibold">{{ card.name }}</p>
        <p v-if="summary" class="font-h3-regular">{{ summary }}</p>
      </section>

      <EmergencyCallButton v-if="contact1" @click="phoneCall(contact1.phone)">
        撥打 {{ contact1.name }}{{ relationText(contact1.relation) }}
      </EmergencyCallButton>
      <SecondaryButton v-if="contact2" @click="phoneCall(contact2.phone)">
        撥打 {{ contact2.name }}{{ relationText(contact2.relation) }}
      </SecondaryButton>

      <InfoList v-if="rows.length" :rows="rows" label="醫療卡內容" />

      <section v-if="medicines.length" class="meds" aria-labelledby="rescue-meds-title">
        <h2 id="rescue-meds-title" class="meds-title font-h3-regular">
          <span class="text-second">目前用藥</span>
          <span class="source">（來自長者的藥單）</span>
        </h2>
        <ul class="meds-list">
          <li v-for="m in medicines" :key="m.code" class="font-h3-semibold">{{ m.name }}｜{{ m.effect }}</li>
        </ul>
      </section>
    </template>
  </PageLayout>
</template>

<style scoped>
.empty {
  padding: 16px;
  border-radius: 12px;
  border: 2px dashed var(--alarm-red-500);
  color: var(--text-primary);
  text-align: center;
}
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
