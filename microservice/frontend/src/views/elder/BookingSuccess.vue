<script setup lang="ts">
/**
 * EL-PG-12 長者：預約成功
 * 返回鍵鎖定回首頁，避免重複送出預約。
 * 提醒文字依規格「規則」：回診提醒實際於回診前 1 小時發送。
 */
import { computed, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import PageLayout from '@/components/PageLayout.vue'
import SuccessBanner from '@/components/alerts/SuccessBanner.vue'
import InfoList from '@/components/cards/InfoList.vue'
import InfoNotice from '@/components/alerts/InfoNotice.vue'
import PrimaryButton from '@/components/buttons/PrimaryButton.vue'
import { state } from '@/store'
import { formatMonthDayWeek } from '@/utils/date'

const router = useRouter()
const appt = computed(() => state.appointment)

const rows = computed(() => {
  const a = appt.value
  if (!a) return []
  return [
    { label: '看診號碼', value: `${a.number} 號` },
    { label: '日期', value: formatMonthDayWeek(a.date) },
    { label: '時段', value: a.timeLabel },
    { label: '院區', value: a.hospital },
    { label: '科別', value: a.department },
    { label: '醫師', value: a.doctor },
  ]
})

const goHome = () => router.replace('/elder')

onMounted(() => {
  if (!appt.value) goHome()
})
</script>

<template>
  <PageLayout title="預約結果" :on-back="goHome">
    <SuccessBanner title="預約成功" />
    <InfoList :rows="rows" label="預約明細" />
    <InfoNotice>回診前 1 小時，您和家屬都會收到提醒。</InfoNotice>
    <div class="flex-spacer" />
    <PrimaryButton @click="goHome">回到首頁</PrimaryButton>
  </PageLayout>
</template>
