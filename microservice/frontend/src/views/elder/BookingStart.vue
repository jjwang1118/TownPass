<script setup lang="ts">
/** EL-PG-09 長者：回診預約；院區／科別依藥單自動帶入，五欄選完 → EL-PG-10 */
import { computed } from 'vue'
import { useRouter } from 'vue-router'
import BookingForm from '@/views/shared/BookingForm.vue'
import { isBookingComplete, prefillBooking, resetBooking } from '@/store'
import { bookingNotice } from './bookingNotice'

const router = useRouter()

// 從其他頁面新進入時重新開始；從 EL-PG-10 返回時保留已選內容
if (!window.history.state?.forward) {
  resetBooking()
  prefillBooking().catch(() => {
    /* 連線錯誤由畫面上方的提示顯示 */
  })
}

const notice = computed(bookingNotice)

function next() {
  if (isBookingComplete()) router.push('/elder/booking/filled')
}
</script>

<template>
  <BookingForm :notice="notice" fallback="/elder" @completed="next" @next="next" />
</template>
