<script setup lang="ts">
/**
 * 回診預約表單共用：EL-PG-09（填寫中）／EL-PG-10（已填好）
 * - 院區 → 科別 → 醫師 依序選（科別要先選院區、醫師要先選科別）
 * - 日期、時段一開始就列出全部，不用等前面欄位；不能預約的（已過、額滿、醫師沒看診）灰階不可選
 * - 以即時時間判斷今天哪些時段已經過了
 * - 選完全部欄位才可按「下一步」
 */
import { computed, ref } from 'vue'
import PageLayout from '@/components/PageLayout.vue'
import InfoNotice from '@/components/alerts/InfoNotice.vue'
import SelectField from '@/components/inputs/SelectField.vue'
import PrimaryButton from '@/components/buttons/PrimaryButton.vue'
import SelectSheet from '@/components/overlays/SelectSheet.vue'
import { BOOKING_FIELDS, isBookingComplete, setBookingField, state, type BookingField } from '@/store'
import { useNow } from '@/composables/useNow'
import {
  BOOKING_LABELS,
  bookingDisplay,
  bookingOptions,
  bookingSheetTitle,
  invalidBookingFields,
} from '@/utils/booking'

defineProps<{ notice: string; fallback: string }>()
const emit = defineEmits<{ completed: []; next: [] }>()

const now = useNow()
const openField = ref<BookingField | null>(null)

const complete = computed(() => isBookingComplete())

/** 只有科別、醫師需要先選上一欄；日期、時段隨時可選 */
function isDisabled(field: BookingField): boolean {
  if (field === 'department') return !state.booking.hospital
  if (field === 'doctor') return !state.booking.department
  return false
}

const sheetOptions = computed(() =>
  openField.value ? bookingOptions(openField.value, state.booking, now.value) : [],
)
const sheetTitle = computed(() => (openField.value ? bookingSheetTitle(openField.value, state.booking) : ''))

/** 清空已經不能預約的日期／時段（例如換了醫師、時間已經過了） */
function clearInvalid() {
  invalidBookingFields(state.booking, new Date()).forEach((f) => setBookingField(f, ''))
}

function select(value: string) {
  if (!openField.value) return
  const wasComplete = complete.value
  setBookingField(openField.value, value)
  openField.value = null
  clearInvalid()
  if (!wasComplete && isBookingComplete()) emit('completed')
}

function next() {
  clearInvalid()
  if (isBookingComplete()) emit('next')
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
    <PrimaryButton :disabled="!complete" @click="next">{{ complete ? '下一步' : '請先選好全部項目' }}</PrimaryButton>

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
