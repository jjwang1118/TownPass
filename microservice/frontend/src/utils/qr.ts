import { SLOT_KEY_BY_NAME } from '@/data/constants'
import type { DraftPrescription, MealTiming, SlotKey } from '@/types'
import { dailyAmount } from './supply'

/**
 * 解析藥袋 QR Code。藥袋 QR Code 格式需與醫院合作制定，目前支援：
 * {"hospital","department","visitDate","days","medicines":[{"name","amount","effect","slots":["早上"],"meal":"飯後","quantity":28}]}
 * - quantity：該藥總顆數；沒有時以 days（給藥天數，預設 28）× 每天吃幾顆 推算
 * 內容不是藥單格式（例如網址、一般文字）時回傳 null，由畫面提示「不是藥袋的 QR Code」，不使用假資料。
 */
export function parsePrescriptionQr(raw: string): DraftPrescription | null {
  try {
    const data = JSON.parse(raw) as Record<string, unknown>
    const meds = Array.isArray(data.medicines) ? (data.medicines as Record<string, unknown>[]) : []
    if (!data.hospital || meds.length === 0 || meds.some((m) => !m?.name)) return null
    return {
      code: '',
      hospital: String(data.hospital),
      department: String(data.department ?? ''),
      visitDate: String(data.visitDate ?? new Date().toISOString().slice(0, 10)),
      medicines: meds.map((m) => {
        const parsedSlots = (Array.isArray(m.slots) ? m.slots : [])
          .map((s) => SLOT_KEY_BY_NAME[String(s)] ?? (s as SlotKey))
          .filter((s): s is SlotKey => ['morning', 'noon', 'evening', 'bedtime'].includes(s))
        const slots: SlotKey[] = parsedSlots.length ? parsedSlots : ['morning']
        const amount = Number(m.amount ?? 1)
        const quantity = Number(m.quantity ?? Number(data.days ?? 28) * dailyAmount({ amount, slots }))
        return {
          code: '',
          name: String(m.name ?? ''),
          amount,
          quantity,
          effect: String(m.effect ?? ''),
          slots,
          meal: (m.meal === '飯前' ? '飯前' : '飯後') as MealTiming,
          checked: false,
        }
      }),
    }
  } catch {
    return null
  }
}
