<script setup lang="ts">
/**
 * 回診預約表單共用：EL-PG-09（填寫中）／EL-PG-10（已填好）
 * 五欄依序鎖定；選完全部欄位才可按「下一步」
 */
import { computed, ref } from 'vue'
import PageLayout from '@/components/PageLayout.vue'
import InfoNotice from '@/components/alerts/InfoNotice.vue'
import SelectField from '@/components/inputs/SelectField.vue'
import PrimaryButton from '@/components/buttons/PrimaryButton.vue'
import SelectSheet from '@/components/overlays/SelectSheet.vue'
import { BOOKING_FIELDS, isBookingComplete, setBookingField, state, type BookingField } from '@/store'
import { BOOKING_LABELS, bookingDisplay, bookingOptions, bookingSheetTitle } from '@/utils/booking'

defineProps<{ notice: string; fallback: string }>()
const emit = defineEmits<{ completed: []; next: [] }>()

const now = new Date()
const openField = ref<BookingField | null>(null)

const complete = computed(() => isBookingComplete())

function isDisabled(field: BookingField): boolean {
  const idx = BOOKING_FIELDS.indexOf(field)
  return BOOKING_FIELDS.slice(0, idx).some((f) => !state.booking[f])
}

const sheetOptions = computed(() => (openField.value ? bookingOptions(openField.value, state.booking, now) : []))
const sheetTitle = computed(() => (openField.value ? bookingSheetTitle(openField.value, state.booking) : ''))

function select(value: string) {
  if (!openField.value) return
  const wasComplete = complete.value
  setBookingField(openField.value, value)
  openField.value = null
  if (!wasComplete && isBookingComplete()) emit('completed')
}

</script>

<template>
  <PageLayout title="回診預約" :fallback="fallback">
    <h2 class="page-heading">預約回診</h2>
    <InfoNotice>{{ notice }}</InfoNotice>
    <SelectField
      v-for="field in BOOKING_FIELDS"
      :key="field"
      :label="BOOKING_LABELS[field]"
      :value="bookingDisplay(field, state.booking)"
      :disabled="isDisabled(field)"
      @open="openField = field"
    />
    <PrimaryButton :disabled="!complete" @click="emit('next')">{{ complete ? '下一步' : '請先選好全部項目' }}</PrimaryButton>

    <SelectSheet
      :open="openField !== null"
      :title="sheetTitle"
      :options="sheetOptions"
      :selected="openField ? state.booking[openField] : ''"
      @close="openField = null"
      @select="select"
    />
  </PageLayout>
</template>
