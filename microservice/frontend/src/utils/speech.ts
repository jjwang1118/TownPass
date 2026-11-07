import type { Lang, Medicine, SlotKey } from '@/types'
import { SLOTS } from '@/data/constants'
import { amountText, slotNames } from './schedule'

/* ---------- 英文（給外籍看護）的念法，和後端 speech 模組一致 ---------- */

const SLOT_EN: Record<SlotKey, string> = {
  morning: 'morning, 9 AM',
  noon: 'noon, 12 PM',
  evening: 'evening, 6 PM',
  bedtime: 'bedtime, 10 PM',
}

/** morning → morning, 9 AM */
export const slotNameEn = (key: SlotKey) => SLOT_EN[key]

/** 1 → 1 tablet；0.5 → half a tablet；1.5 → 1 and a half tablets */
function amountEn(amount: number): string {
  const whole = Math.floor(amount)
  const half = amount - whole >= 0.5
  if (whole === 0) return 'half a tablet'
  if (half) return `${whole} and a half tablets`
  return whole === 1 ? '1 tablet' : `${whole} tablets`
}

const UNIT_EN: [RegExp, string][] = [
  [/\s*毫克/g, 'mg'],
  [/\s*微克/g, 'mcg'],
  [/\s*毫升/g, 'ml'],
]

/** Lipitor 10 毫克 → Lipitor 10mg；英文語音念不出中文，換完單位仍有中文的藥名（脈優錠）不念 */
function drugNameEn(name: string): string {
  const en = UNIT_EN.reduce((s, [re, unit]) => s.replace(re, unit), name).trim()
  return /[㐀-鿿]/.test(en) ? '' : en
}

function medicineSpeechEn(m: Medicine, withSlot: boolean): string {
  if (m.speechEn) return m.speechEn // 已加入的藥：後端的英文稿（英文藥名、科別、用途）
  const head = [`Medicine ${m.code}`, drugNameEn(m.name)].filter(Boolean).join(', ')
  const meal = m.meal === '飯前' ? 'before meals' : 'after meals'
  const slots = SLOTS.filter((s) => m.slots.includes(s.key)).map((s) => SLOT_EN[s.key])
  const when = withSlot && slots.length ? `, ${slots.join(' and ')}` : ''
  return `${head}. Take ${amountEn(m.amount)} ${meal}${when}.`
}

/* ---------- 朗讀稿 ---------- */

/** 單顆朗讀：B1，Metformin 500 毫克，1 顆，降血糖，飯後 */
export function medicineSpeech(m: Medicine, withSlot = false, lang: Lang = 'zh'): string {
  if (lang === 'en') return medicineSpeechEn(m, withSlot)
  const parts = [m.code, m.name, amountText(m.amount), m.effect, withSlot ? slotNames(m.slots) : '', m.meal]
  return parts.filter(Boolean).join('，')
}

/** 整區朗讀：中午 12:00 要吃的藥，共 2 顆藥。B1，…。B2，…。title 由呼叫端依語言傳入 */
export function slotSpeech(title: string, meds: Medicine[], lang: Lang = 'zh'): string {
  if (lang === 'en') {
    if (meds.length === 0) return `${title}. No medicine at this time.`
    const count = meds.length === 1 ? '1 medicine' : `${meds.length} medicines`
    return `${title}. ${count}. ${meds.map((m) => medicineSpeechEn(m, false)).join(' ')}`
  }
  if (meds.length === 0) return `${title}，這個時段不用吃藥。`
  return `${title}，共 ${meds.length} 種藥。${meds.map((m) => medicineSpeech(m)).join('。')}。`
}
