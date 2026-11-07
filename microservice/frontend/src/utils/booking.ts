/**
 * 回診預約各欄的選項（UI E10）：資料來自後端（store 的 bookingData），由 loadBookingOptions() 讀取。
 * 院區 → 科別 → 醫師 → 日期 → 時段依序選；額滿、停診的以灰階顯示並說明原因。
 */
import { state, type BookingField } from '@/store'
import { shortHospital } from '@/api/mappers'
import type { BookingDraft, SelectOption } from '@/types'

export const BOOKING_LABELS: Record<BookingField, string> = {
  hospital: '院區',
  department: '科別',
  doctor: '醫師',
  date: '日期',
  time: '時段',
}

export function bookingOptions(field: BookingField, b: BookingDraft): SelectOption[] {
  const data = state.bookingData
  switch (field) {
    case 'hospital':
      return data.hospitals.map((h) => ({ value: h.id, label: shortHospital(h.name), subtitle: h.address }))
    case 'department':
      return (data.departments[b.hospitalId ?? ''] ?? []).map((d) => ({
        value: d.id,
        label: d.name,
        subtitle: d.from_letter ? `藥單 ${d.from_letter} 的科別` : undefined,
      }))
    case 'doctor':
      return (data.doctors[b.departmentId ?? ''] ?? []).map((d) => ({
        value: d.id,
        label: d.name,
        subtitle: d.note ?? d.schedule,
        disabled: !d.available,
      }))
    case 'date':
      return (data.sessions[b.doctorId ?? ''] ?? []).map((s) => ({
        value: s.session_id,
        label: `${s.label} ${s.period_label}`,
        subtitle: s.note ?? s.period_label,
        disabled: !s.available,
      }))
    case 'time':
      return (data.slots[b.date] ?? []).map((s) => ({
        value: s.slot_id,
        label: s.label,
        subtitle: s.note,
        disabled: !s.available,
      }))
  }
}

/** 欄位顯示值 */
export function bookingDisplay(field: BookingField, b: BookingDraft): string {
  if (field === 'date') return b.dateLabel ?? ''
  if (field === 'time') return b.timeLabel ?? ''
  return b[field]
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
      return b.doctor ? `${base}（${b.doctor}的門診日）` : base
    case 'time':
      return b.dateLabel ? `${base}（${b.dateLabel}）` : base
    default:
      return base
  }
}
