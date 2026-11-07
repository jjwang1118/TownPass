import { RECOGNIZED_PRESCRIPTION } from '@/data/mock'
import { SLOT_KEY_BY_NAME } from '@/data/constants'
import type { DraftPrescription, MealTiming, SlotKey } from '@/types'

/**
 * 解析藥袋 QR Code。藥袋 QR Code 格式需與醫院合作制定，目前支援：
 * {"hospital","department","visitDate","days","medicines":[{"name","amount","effect","slots":["早上"],"meal":"飯後"}]}
 * 無法解析時使用模擬辨識結果。
 */
export function parsePrescriptionQr(raw: string): DraftPrescription {
  try {
    const data = JSON.parse(raw) as Record<string, unknown>
    const meds = Array.isArray(data.medicines) ? (data.medicines as Record<string, unknown>[]) : []
    if (!data.hospital || meds.length === 0) return RECOGNIZED_PRESCRIPTION
    return {
      code: '',
      hospital: String(data.hospital),
      department: String(data.department ?? ''),
      visitDate: String(data.visitDate ?? new Date().toISOString().slice(0, 10)),
      days: Number(data.days ?? 28),
      medicines: meds.map((m) => {
        const slots = (Array.isArray(m.slots) ? m.slots : [])
          .map((s) => SLOT_KEY_BY_NAME[String(s)] ?? (s as SlotKey))
          .filter((s): s is SlotKey => ['morning', 'noon', 'evening', 'bedtime'].includes(s))
        return {
          code: '',
          name: String(m.name ?? ''),
          amount: Number(m.amount ?? 1),
          effect: String(m.effect ?? ''),
          slots: slots.length ? slots : ['morning'],
          meal: (m.meal === '飯前' ? '飯前' : '飯後') as MealTiming,
          checked: false,
        }
      }),
    }
  } catch {
    return RECOGNIZED_PRESCRIPTION
  }
}
