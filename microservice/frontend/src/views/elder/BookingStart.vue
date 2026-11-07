<script setup lang="ts">
/** EL-PG-09 長者：回診預約；院區／科別依藥單自動帶入，五欄選完 → EL-PG-10 */
import { useRouter } from 'vue-router'
import BookingForm from '@/views/shared/BookingForm.vue'
import { isBookingComplete, resetBooking } from '@/store'
import { bookingNotice, prefillPrescription } from './bookingNotice'

const router = useRouter()

// 從其他頁面新進入時重新開始；從 EL-PG-10 返回時保留已選內容
if (!window.history.state?.forward) {
  const rx = prefillPrescription()
  resetBooking(rx ? { hospital: rx.hospital, department: rx.department } : undefined)
}

const notice = bookingNotice()

function next() {
  if (isBookingComplete()) router.push('/elder/booking/filled')
}
</script>

<template>
  <BookingForm :notice="notice" fallback="/elder" @completed="next" @next="next" />
</template>
