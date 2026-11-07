<script setup lang="ts">
/** EL-PG-11 長者：確認預約 */
import { computed, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import PageLayout from '@/components/PageLayout.vue'
import InfoList from '@/components/cards/InfoList.vue'
import WarningNotice from '@/components/alerts/WarningNotice.vue'
import PrimaryButton from '@/components/buttons/PrimaryButton.vue'
import SecondaryButton from '@/components/buttons/SecondaryButton.vue'
import { BOOKING_FIELDS, confirmBooking, isBookingComplete, state } from '@/store'
import { BOOKING_LABELS, bookingDisplay } from '@/utils/booking'

const router = useRouter()

const rows = computed(() =>
  BOOKING_FIELDS.map((f) => ({ label: BOOKING_LABELS[f], value: bookingDisplay(f, state.booking) })),
)

function backToForm() {
  if (window.history.state?.back) router.back()
  else router.replace('/elder/booking/filled')
}

function confirm() {
  confirmBooking(bookingDisplay('time', state.booking))
  router.push('/elder/booking/done')
}

onMounted(() => {
  if (!isBookingComplete()) router.replace('/elder/booking')
})
</script>

<template>
  <PageLayout title="確認預約" :on-back="backToForm">
    <h2 class="page-heading">請確認預約資料</h2>
    <InfoList :rows="rows" label="預約資料" />
    <WarningNotice>看診當天請記得帶健保卡。</WarningNotice>
    <div class="flex-spacer" />
    <PrimaryButton @click="confirm">確認預約</PrimaryButton>
    <SecondaryButton @click="backToForm">修改</SecondaryButton>
  </PageLayout>
</template>
