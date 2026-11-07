<script setup lang="ts">
/**
 * 回診預約表單共用：EL-PG-09（填寫中）／EL-PG-10（已填好）
 * - 院區 → 科別 → 醫師 → 日期 → 時段依序選（UI E10：選單依序啟用；更換前一項時清空後面的選擇）
 * - 選項來自後端：打開選單時讀取（時段每次重新讀取，剩餘名額才是即時的）
 * - 額滿、停診的選項以灰階顯示並說明原因
 * - 選完全部欄位才可按「下一步」
 */
import { computed, ref } from 'vue'
import PageLayout from '@/components/PageLayout.vue'
import InfoNotice from '@/components/alerts/InfoNotice.vue'
import SelectField from '@/components/inputs/SelectField.vue'
import PrimaryButton from '@/components/buttons/PrimaryButton.vue'
import SelectSheet from '@/components/overlays/SelectSheet.vue'
import {
  BOOKING_FIELDS,
  bookingPrerequisite,
  isBookingComplete,
  loadBookingOptions,
  setBookingField,
  state,
  type BookingField,
} from '@/store'
import { BOOKING_LABELS, bookingDisplay, bookingOptions, bookingSheetTitle } from '@/utils/booking'

defineProps<{ notice: string; fallback: string }>()
const emit = defineEmits<{ completed: []; next: [] }>()

const openField = ref<BookingField | null>(null)

const complete = computed(() => isBookingComplete())

/** 要先選好前一欄 */
function isDisabled(field: BookingField): boolean {
  const before = bookingPrerequisite(field)
  return before !== null && !state.booking[before]
}

const sheetOptions = computed(() => (openField.value ? bookingOptions(openField.value, state.booking) : []))
const sheetTitle = computed(() => (openField.value ? bookingSheetTitle(openField.value, state.booking) : ''))

/** 目前選到的值（院區、科別、醫師存 id；日期、時段存門診與看診時間的 id） */
function selectedValue(field: BookingField): string {
  const b = state.booking
  if (field === 'hospital') return b.hospitalId ?? ''
  if (field === 'department') return b.departmentId ?? ''
  if (field === 'doctor') return b.doctorId ?? ''
  return b[field]
}

async function open(field: BookingField) {
  openField.value = field
  try {
    await loadBookingOptions(field)
  } catch {
    /* 連線錯誤由畫面上方的提示顯示 */
  }
}

function select(value: string) {
  if (!openField.value) return
  const wasComplete = complete.value
  const label = sheetOptions.value.find((o) => o.value === value)?.label ?? ''
  setBookingField(openField.value, value, label)
  openField.value = null
  if (!wasComplete && isBookingComplete()) emit('completed')
}

function next() {
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
      @open="open(field)"
    />
    <PrimaryButton :disabled="!complete" @click="next">{{ complete ? '下一步' : '請先選好全部項目' }}</PrimaryButton>

    <SelectSheet
      :open="openField !== null"
      :title="sheetTitle"
      :options="sheetOptions"
      :selected="openField ? selectedValue(openField) : ''"
      @close="openField = null"
      @select="select"
    />
  </PageLayout>
</template>
