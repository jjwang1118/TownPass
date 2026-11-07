<script setup lang="ts">
/** EL-PG-11 長者：確認預約 */
import { computed, onMounted, ref } from 'vue'
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

const submitting = ref(false)
const error = ref('')

async function confirm() {
  if (submitting.value) return
  submitting.value = true
  error.value = ''
  try {
    await confirmBooking()
    router.push('/elder/booking/done')
  } catch (e) {
    // 例如剛好被別人約滿：請長者回上一頁重選時段
    error.value = e instanceof Error ? e.message : '預約失敗，請再試一次'
  } finally {
    submitting.value = false
  }
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
    <WarningNotice v-if="error" role="alert">{{ error }}，請按「修改」重新選擇。</WarningNotice>
    <div class="flex-spacer" />
    <PrimaryButton :disabled="submitting" @click="confirm">{{ submitting ? '預約中…' : '確認預約' }}</PrimaryButton>
    <SecondaryButton @click="backToForm">修改</SecondaryButton>
  </PageLayout>
</template>
