<script setup lang="ts">
/** EL-PG-10 長者：回診預約（已填好）；任一欄可重選，改前面欄位時後面需重選 */
import { onMounted } from 'vue'
import { useRouter } from 'vue-router'
import BookingForm from '@/views/shared/BookingForm.vue'
import { isBookingComplete } from '@/store'
import { bookingNotice } from './bookingNotice'

const router = useRouter()
const notice = bookingNotice()

onMounted(() => {
  if (!isBookingComplete()) router.replace('/elder/booking')
})
</script>

<template>
  <BookingForm :notice="notice" fallback="/elder/booking" @next="router.push('/elder/booking/confirm')" />
</template>
