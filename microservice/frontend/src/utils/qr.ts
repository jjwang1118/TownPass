import { SLOT_KEY_BY_NAME } from '@/data/constants'
import type { DraftPrescription, MealTiming, SlotKey } from '@/types'
import { dailyAmount } from './supply'

/**
 * 解析藥袋二維碼（格式說明見 microservice/docs/qrcode_format.md）
 *
 * {
 *   "hospital": "仁愛院區",            // 必填：醫院／院區
 *   "department": "心臟科",             // 選填：科別
 *   "visitDate": "2026-11-08",          // 選填：看診（領藥）日，YYYY-MM-DD 或民國 115.11.08，預設今天
 *   "days": 28,                         // 選填：給藥天數，藥品沒有 quantity 時用來推算總顆數
 *   "medicines": [                      // 必填：至少 1 筆
 *     {
 *       "name": "Aspirin 100 毫克",       // 必填：藥名＋劑量
 *       "amount": 1,                      // 選填：一次幾顆（0.5 為單位），預設 1
 *       "slots": ["早上"],                // 選填：早上／中午／晚上／睡前；與 frequency 擇一，預設早上
 *       "frequency": "TID",               // 選填：頻率代碼 QD／BID／TID／QID／HS／q8h／q12h…，沒有 slots 時換算
 *       "meal": "飯後",                   // 選填：飯前／飯後，預設飯後
 *       "effect": "預防血栓",             // 選填：功效
 *       "quantity": 28                    // 選填：總顆數，用來算還剩幾天
 *     }
 *   ]
 * }
 */

export type QrParseResult =
  | { ok: true; rx: DraftPrescription }
  | { ok: false; reason: 'not_prescription' }
  | { ok: false; reason: 'missing'; missing: string[] }

/** 頻率代碼 → 時段（大小寫不拘） */
const FREQUENCY_SLOTS: Record<string, SlotKey[]> = {
  QD: ['morning'],
  QAM: ['morning'],
  QN: ['bedtime'],
  HS: ['bedtime'],
  QPM: ['evening'],
  BID: ['morning', 'evening'],
  Q12H: ['morning', 'evening'],
  TID: ['morning', 'noon', 'evening'],
  Q8H: ['morning', 'noon', 'evening'],
  QID: ['morning', 'noon', 'evening', 'bedtime'],
  Q6H: ['morning', 'noon', 'evening', 'bedtime'],
}

const SLOT_KEYS: SlotKey[] = ['morning', 'noon', 'evening', 'bedtime']

function toSlots(m: Record<string, unknown>): SlotKey[] {
  const fromSlots = (Array.isArray(m.slots) ? m.slots : [])
    .map((s) => SLOT_KEY_BY_NAME[String(s)] ?? (s as SlotKey))
    .filter((s): s is SlotKey => SLOT_KEYS.includes(s))
  if (fromSlots.length) return fromSlots
  const freq = String(m.frequency ?? '').replace(/\s/g, '').toUpperCase()
  return FREQUENCY_SLOTS[freq] ?? ['morning']
}

/** YYYY-MM-DD、YYYY/MM/DD 或民國年 115.11.08／115/11/08 → YYYY-MM-DD；無法辨識回傳今天 */
function toIsoDate(value: unknown): string {
  const pad = (n: number) => String(n).padStart(2, '0')
  const m = String(value ?? '').trim().match(/^(\d{2,4})[-/.](\d{1,2})[-/.](\d{1,2})$/)
  if (m) {
    let year = Number(m[1])
    if (year < 1911) year += 1911 // 民國年
    return `${year}-${pad(Number(m[2]))}-${pad(Number(m[3]))}`
  }
  const d = new Date()
  return `${d.getFullYear()}-${pad(d.getMonth() + 1)}-${pad(d.getDate())}`
}

export function parsePrescriptionQr(raw: string): QrParseResult {
  let data: Record<string, unknown>
  try {
    data = JSON.parse(raw) as Record<string, unknown>
  } catch {
    return { ok: false, reason: 'not_prescription' }
  }
  if (!data || typeof data !== 'object' || Array.isArray(data)) return { ok: false, reason: 'not_prescription' }

  const meds = Array.isArray(data.medicines) ? (data.medicines as Record<string, unknown>[]) : []
  const missing: string[] = []
  if (!String(data.hospital ?? '').trim()) missing.push('院區（hospital）')
  if (meds.length === 0) missing.push('藥品清單（medicines）')
  else if (meds.some((m) => !String(m?.name ?? '').trim())) missing.push('藥名（medicines[].name）')
  if (missing.length) return { ok: false, reason: 'missing', missing }

  const days = Number(data.days ?? 28)
  return {
    ok: true,
    rx: {
      code: '',
      hospital: String(data.hospital).trim(),
      department: String(data.department ?? '').trim(),
      visitDate: toIsoDate(data.visitDate),
      medicines: meds.map((m) => {
        const slots = toSlots(m)
        const amount = Number(m.amount ?? 1) > 0 ? Number(m.amount ?? 1) : 1
        const quantity = Number(m.quantity ?? days * dailyAmount({ amount, slots }))
        return {
          code: '',
          name: String(m.name).trim(),
          amount,
          quantity: quantity > 0 ? quantity : days * dailyAmount({ amount, slots }),
          effect: String(m.effect ?? '').trim(),
          slots,
          meal: (m.meal === '飯前' ? '飯前' : '飯後') as MealTiming,
          checked: false,
        }
      }),
    },
  }
}
