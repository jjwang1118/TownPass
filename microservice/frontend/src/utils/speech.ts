import type { Medicine } from '@/types'
import { amountText, slotNames } from './schedule'

/** 單顆朗讀：B1，Metformin 500 毫克，1 顆，降血糖，飯後 */
export function medicineSpeech(m: Medicine, withSlot = false): string {
  const parts = [m.code, m.name, amountText(m.amount), m.effect, withSlot ? slotNames(m.slots) : '', m.meal]
  return parts.filter(Boolean).join('，')
}

/** 整區朗讀：中午 12:00 要吃的藥，共 2 顆藥。B1，…。B2，…。 */
export function slotSpeech(title: string, meds: Medicine[]): string {
  if (meds.length === 0) return `${title}，這個時段不用吃藥。`
  return `${title}，共 ${meds.length} 種藥。${meds.map((m) => medicineSpeech(m)).join('。')}。`
}
