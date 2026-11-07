import { DEPARTMENTS, HOSPITALS, TIME_SLOTS, doctorsOf, isTimeFull, weekdayText } from '@/data/mock'
import type { BookingField } from '@/store'
import type { BookingDraft, SelectOption } from '@/types'
import { addDays, formatMonthDayWeek, toISODate } from './date'

export const BOOKING_LABELS: Record<BookingField, string> = {
  hospital: '院區',
  department: '科別',
  doctor: '醫師',
  date: '日期',
  time: '時段',
}

/** 依上層已選條件篩選選項（院區 → 科別 → 醫師 → 日期 → 時段） */
export function bookingOptions(field: BookingField, b: BookingDraft, now: Date): SelectOption[] {
  switch (field) {
    case 'hospital':
      return HOSPITALS.map((h) => ({ value: h, label: h }))
    case 'department':
      return (DEPARTMENTS[b.hospital] ?? []).map((d) => ({ value: d, label: d }))
    case 'doctor':
      return doctorsOf(b.hospital, b.department).map((d) => ({
        value: d.name,
        label: d.name,
        subtitle: d.full ? '本月已額滿' : `${weekdayText(d.weekdays)}看診`,
        disabled: d.full,
      }))
    case 'date': {
      const doc = doctorsOf(b.hospital, b.department).find((d) => d.name === b.doctor)
      if (!doc) return []
      const list: SelectOption[] = []
      for (let i = 1; i <= 28; i += 1) {
        const d = addDays(now, i)
        if (!doc.weekdays.includes(d.getDay())) continue
        const iso = toISODate(d)
        list.push({ value: iso, label: formatMonthDayWeek(iso) })
      }
      return list
    }
    case 'time':
      return TIME_SLOTS.map((t) => {
        const full = isTimeFull(b.date, t.time)
        return { value: t.time, label: t.label, subtitle: full ? '已額滿' : undefined, disabled: full }
      })
  }
}

/** 欄位顯示值 */
export function bookingDisplay(field: BookingField, b: BookingDraft): string {
  const v = b[field]
  if (!v) return ''
  if (field === 'date') return formatMonthDayWeek(v)
  if (field === 'time') return TIME_SLOTS.find((t) => t.time === v)?.label ?? v
  return v
}

/** 抽屜標題：選擇醫師（仁愛院區 心臟科） */
export function bookingSheetTitle(field: BookingField, b: BookingDraft): string {
  const base = `選擇${BOOKING_LABELS[field]}`
  switch (field) {
    case 'department':
      return `${base}（${b.hospital}）`
    case 'doctor':
      return `${base}（${b.hospital} ${b.department}）`
    case 'date':
      return `${base}（${b.doctor}）`
    case 'time':
      return `${base}（${formatMonthDayWeek(b.date)}）`
    default:
      return base
  }
}
