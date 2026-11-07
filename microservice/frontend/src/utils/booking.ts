import { DEPARTMENTS, HOSPITALS, TIME_SLOTS, doctorsOf, isTimeFull, weekdayText } from '@/data/mock'
import type { BookingField } from '@/store'
import type { BookingDraft, SelectOption } from '@/types'
import { addDays, formatClock, formatMonthDayWeek, parseDate, toISODate } from './date'

export const BOOKING_LABELS: Record<BookingField, string> = {
  hospital: '院區',
  department: '科別',
  doctor: '醫師',
  date: '日期',
  time: '時段',
}

/** 可預約日期範圍：今天起 28 天 */
const BOOKING_DAYS = 28

function selectedDoctor(b: BookingDraft) {
  return doctorsOf(b.hospital, b.department).find((d) => d.name === b.doctor)
}

/** 這個時段現在還能不能預約（已額滿、今天已過的時段不能選） */
export function isTimeAvailable(date: string, time: string, now: Date): boolean {
  if (date && isTimeFull(date, time)) return false
  if (date === toISODate(now) && time <= formatClock(now)) return false
  return true
}

function timeUnavailableReason(date: string, time: string, now: Date): string | undefined {
  if (date === toISODate(now) && time <= formatClock(now)) return '已經過了'
  if (date && isTimeFull(date, time)) return '已額滿'
  return undefined
}

/** 這一天能不能預約：選了醫師要看他那天有沒有看診；今天要還有沒過的時段 */
export function isDateAvailable(b: BookingDraft, date: string, now: Date): boolean {
  const doc = selectedDoctor(b)
  if (doc && !doc.weekdays.includes(parseDate(date).getDay())) return false
  return TIME_SLOTS.some((t) => isTimeAvailable(date, t.time, now))
}

/**
 * 各欄選項
 * - 院區 → 科別 → 醫師 依序相依
 * - 日期、時段一開始就列出全部，不能預約的以灰階顯示並說明原因
 */
export function bookingOptions(field: BookingField, b: BookingDraft, now: Date): SelectOption[] {
  switch (field) {
    case 'hospital':
      return HOSPITALS.map((h) => ({ value: h, label: h }))
    case 'department':
      return (DEPARTMENTS[b.hospital] ?? []).map((d) => ({ value: d, label: d }))
    case 'doctor': {
      const weekday = b.date ? parseDate(b.date).getDay() : null
      return doctorsOf(b.hospital, b.department).map((d) => {
        const offThatDay = weekday !== null && !d.weekdays.includes(weekday)
        let subtitle = `${weekdayText(d.weekdays)}看診`
        if (d.full) subtitle = '本月已額滿'
        else if (offThatDay) subtitle = `${formatMonthDayWeek(b.date)}沒有看診（${weekdayText(d.weekdays)}看診）`
        return { value: d.name, label: d.name, subtitle, disabled: d.full || offThatDay }
      })
    }
    case 'date': {
      const doc = selectedDoctor(b)
      const today = toISODate(now)
      const list: SelectOption[] = []
      for (let i = 0; i < BOOKING_DAYS; i += 1) {
        const iso = toISODate(addDays(now, i))
        const label = `${formatMonthDayWeek(iso)}${iso === today ? '　今天' : ''}`
        let subtitle: string | undefined
        if (doc && !doc.weekdays.includes(parseDate(iso).getDay())) subtitle = `${doc.name}沒有看診`
        else if (!TIME_SLOTS.some((t) => isTimeAvailable(iso, t.time, now))) subtitle = '這天的時段都不能預約了'
        list.push({ value: iso, label, subtitle, disabled: !!subtitle })
      }
      return list
    }
    case 'time':
      return TIME_SLOTS.map((t) => {
        const reason = timeUnavailableReason(b.date, t.time, now)
        return { value: t.time, label: t.label, subtitle: reason, disabled: !!reason }
      })
  }
}

/** 選完某欄後，已選但變得不能預約的欄位（需清空重選） */
export function invalidBookingFields(b: BookingDraft, now: Date): BookingField[] {
  const invalid: BookingField[] = []
  if (b.date && !isDateAvailable(b, b.date, now)) invalid.push('date')
  if (b.time && !isTimeAvailable(invalid.includes('date') ? '' : b.date, b.time, now)) invalid.push('time')
  return invalid
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
      return b.doctor ? `${base}（${b.doctor}）` : base
    case 'time':
      return b.date ? `${base}（${formatMonthDayWeek(b.date)}）` : base
    default:
      return base
  }
}
