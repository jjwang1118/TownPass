import { SLOTS, type SlotDef } from '@/data/constants'
import type { MedicineWithRx } from '@/store'
import type { Prescription, SlotKey, SlotStatus } from '@/types'

/**
 * 時段狀態：已經過了的時段為「已過」；尚未到的第一個時段為「現在」；其餘為「等一下」。
 * （規格範例：11:40 時，早上已過、中午為現在）
 */
export function slotStatuses(now: Date): Record<SlotKey, SlotStatus> {
  const minutes = now.getHours() * 60 + now.getMinutes()
  const nowSlot = SLOTS.find((s) => s.minutes >= minutes)
  return Object.fromEntries(
    SLOTS.map((s) => {
      if (s.minutes < minutes) return [s.key, 'past']
      if (nowSlot && s.key === nowSlot.key) return [s.key, 'now']
      return [s.key, 'later']
    }),
  ) as Record<SlotKey, SlotStatus>
}

/** 下一次吃藥的時段：今天尚未到且有藥的第一個時段；今天都過了則為明天第一個有藥的時段 */
export function nextMedicineSlot(
  now: Date,
  meds: MedicineWithRx[],
): { slot: SlotDef; tomorrow: boolean } | null {
  const minutes = now.getHours() * 60 + now.getMinutes()
  const withMeds = SLOTS.filter((s) => meds.some((m) => m.slots.includes(s.key)))
  if (withMeds.length === 0) return null
  const today = withMeds.find((s) => s.minutes >= minutes)
  if (today) return { slot: today, tomorrow: false }
  return { slot: withMeds[0], tomorrow: true }
}

export function medicinesInSlot(meds: MedicineWithRx[], slot: SlotKey): MedicineWithRx[] {
  return meds.filter((m) => m.slots.includes(slot))
}

/** 依藥單分組（EL-PG-03／FM-PG-04 分類標籤：B　新陳代謝科｜中興院區） */
export function groupByPrescription(meds: MedicineWithRx[]): { rx: Prescription; medicines: MedicineWithRx[] }[] {
  const groups = new Map<string, { rx: Prescription; medicines: MedicineWithRx[] }>()
  meds.forEach((m) => {
    const g = groups.get(m.rx.code) ?? { rx: m.rx, medicines: [] }
    g.medicines.push(m)
    groups.set(m.rx.code, g)
  })
  return [...groups.values()]
}

/** 1 → 1 顆；0.5 → 半顆；1.5 → 1 顆半 */
export function amountText(amount: number): string {
  const whole = Math.floor(amount)
  const half = amount - whole >= 0.5
  if (whole === 0) return '半顆'
  return half ? `${whole} 顆半` : `${whole} 顆`
}

export function slotNames(keys: SlotKey[]): string {
  return SLOTS.filter((s) => keys.includes(s.key))
    .map((s) => s.name)
    .join('、')
}
