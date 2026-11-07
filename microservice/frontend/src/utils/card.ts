import type { Contact, EmergencyCard } from '@/types'
import { ageOf } from './date'

/** 空白的緊急醫療卡（第一次使用時為空，由長者自行填寫） */
export function emptyCard(): EmergencyCard {
  return {
    name: '',
    birthday: '',
    gender: '',
    bloodType: '',
    contact1: { name: '', relation: '', phone: '' },
    chronic: [],
    drugAllergy: '',
    foodAllergy: '',
    special: [],
    language: '',
    consent: false,
    updatedAt: '',
  }
}

const filled = (s: string | undefined | null) => !!s && s.trim() !== ''

export function hasContact(c: Contact | null | undefined): c is Contact {
  return !!c && (filled(c.name) || filled(c.phone))
}

/** 78 歲｜女｜O 型（沒填的項目不顯示） */
export function cardSummary(card: EmergencyCard, now: Date): string {
  const age = card.age ?? ageOf(card.birthday, now)
  let blood = ''
  if (card.bloodType === '不知道') blood = '血型不知道'
  else if (card.bloodType) blood = `${card.bloodType} 型`
  return [age != null ? `${age} 歲` : '', card.gender, blood].filter(Boolean).join('｜')
}

/** 陳小華（女兒）0912-345-678（沒填的部分不顯示） */
export function contactText(c: Contact): string {
  const relation = filled(c.relation) ? `（${c.relation}）` : ''
  const phone = filled(c.phone) ? ` ${c.phone}` : ''
  return `${c.name}${relation}${phone}`.trim()
}

export function listText(list: string[]): string {
  return list.length ? list.join('、') : '無'
}

export interface CardRow {
  label: string
  value: string
}

/** 有填的欄位才列出：上半部（聯絡人、慢性病、過敏）／下半部（特殊狀況、慣用語言）。不收集常去醫院與病歷號（UI E14） */
export function cardRows(card: EmergencyCard): { top: CardRow[]; bottom: CardRow[] } {
  const top: CardRow[] = []
  if (hasContact(card.contact1)) top.push({ label: '緊急聯絡人', value: contactText(card.contact1) })
  if (card.chronic.length) top.push({ label: '慢性病', value: card.chronic.join('、') })
  if (filled(card.drugAllergy)) top.push({ label: '藥物過敏', value: card.drugAllergy })
  if (filled(card.foodAllergy)) top.push({ label: '食物過敏', value: card.foodAllergy })

  const bottom: CardRow[] = []
  if (card.special.length) bottom.push({ label: '特殊狀況', value: card.special.join('、') })
  if (card.language) bottom.push({ label: '慣用語言', value: card.language })
  return { top, bottom }
}

/** 醫療卡是否完全沒有填寫任何資料 */
export function isCardEmpty(card: EmergencyCard): boolean {
  const { top, bottom } = cardRows(card)
  return !filled(card.name) && !cardSummary(card, new Date()) && top.length === 0 && bottom.length === 0
}
