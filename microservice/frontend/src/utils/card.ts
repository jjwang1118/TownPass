import type { Contact, EmergencyCard } from '@/types'
import { ageOf } from './date'

/** 78 歲｜女｜O 型 */
export function cardSummary(card: EmergencyCard, now: Date): string {
  const age = ageOf(card.birthday, now)
  const blood = card.bloodType === '不知道' || !card.bloodType ? '血型不知道' : `${card.bloodType} 型`
  return [age != null ? `${age} 歲` : '', card.gender, blood].filter(Boolean).join('｜')
}

/** 陳小華（女兒）0912-345-678 */
export function contactText(c: Contact): string {
  return `${c.name}（${c.relation}）${c.phone}`
}

export function listText(list: string[]): string {
  return list.length ? list.join('、') : '無'
}
