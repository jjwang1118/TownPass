<script setup lang="ts">
/** FM-PG-06 家屬：救護人員查看通知（由系統推播開啟） */
import { computed } from 'vue'
import { useRouter } from 'vue-router'
import PageLayout from '@/components/PageLayout.vue'
import AppIcon from '@/components/AppIcon.vue'
import InfoList from '@/components/cards/InfoList.vue'
import SevereNotice from '@/components/alerts/SevereNotice.vue'
import PrimaryButton from '@/components/buttons/PrimaryButton.vue'
import SecondaryButton from '@/components/buttons/SecondaryButton.vue'
import { RESCUE_NOTICE_EXAMPLE } from '@/data/mock'
import { state } from '@/store'
import { phoneCall } from '@/composables/flutterBridge'
import { formatDateTime } from '@/utils/date'

const router = useRouter()

const notice = computed(() => state.rescueNotices[0] ?? RESCUE_NOTICE_EXAMPLE)
const rows = computed(() => [
  { label: '時間', value: formatDateTime(notice.value.time) },
  { label: '單位', value: notice.value.unit },
  { label: '人員編號', value: notice.value.staffId },
])

const goHome = () => router.replace('/family/home')
</script>

<template>
  <PageLayout title="通知" :on-back="goHome">
    <section class="headline">
      <span class="icon"><AppIcon name="bell" :size="48" /></span>
      <h2 class="page-heading">救護人員查看了<br />{{ state.elder.name }}的緊急醫療卡</h2>
    </section>
    <InfoList :rows="rows" label="查看明細" />
    <SevereNotice>長輩可能需要緊急協助，請盡快聯絡。</SevereNotice>
    <div class="flex-spacer" />
    <PrimaryButton @click="phoneCall(state.elder.phone)">打電話給長輩</PrimaryButton>
    <SecondaryButton @click="goHome">回到首頁</SecondaryButton>
  </PageLayout>
</template>

<style scoped>
.headline {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 12px;
  text-align: center;
  padding-top: 8px;
}
.icon {
  width: 96px;
  height: 96px;
  border-radius: 48px;
  background: #fbeceb;
  color: var(--alarm-red-500);
  display: flex;
  align-items: center;
  justify-content: center;
}
</style>
