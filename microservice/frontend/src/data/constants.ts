import type { SlotKey } from '@/types'

export interface SlotDef {
  key: SlotKey
  name: string
  time: string
  /** 從 00:00 起算的分鐘數 */
  minutes: number
}

export const SLOTS: SlotDef[] = [
  { key: 'morning', name: '早上', time: '09:00', minutes: 9 * 60 },
  { key: 'noon', name: '中午', time: '12:00', minutes: 12 * 60 },
  { key: 'evening', name: '晚上', time: '18:00', minutes: 18 * 60 },
  { key: 'bedtime', name: '睡前', time: '22:00', minutes: 22 * 60 },
]

export const SLOT_BY_KEY: Record<SlotKey, SlotDef> = Object.fromEntries(
  SLOTS.map((s) => [s.key, s]),
) as Record<SlotKey, SlotDef>

export const SLOT_KEY_BY_NAME: Record<string, SlotKey> = Object.fromEntries(
  SLOTS.map((s) => [s.name, s.key]),
)

/** EL-SEG-02 各欄位選項 */
export const GENDER_OPTIONS = ['女', '男'] as const
export const BLOOD_OPTIONS = ['A', 'B', 'O', 'AB', '不知道'] as const
export const CHRONIC_OPTIONS = [
  '高血壓',
  '糖尿病',
  '心臟病',
  '腎臟病',
  '中風病史',
  '失智',
  '氣喘或肺病',
  '其他',
] as const
export const SPECIAL_OPTIONS = ['心律調節器', '洗腎', '使用氧氣', '行動不便'] as const
export const LANGUAGE_OPTIONS = ['國語', '台語', '客語'] as const
export const MEAL_OPTIONS = ['飯前', '飯後'] as const

/** 邀請碼有效分鐘數（EL-PG-17） */
export const INVITE_VALID_MINUTES = 10
/** 救護人員醫療卡頁自動關閉分鐘數（RE-PG-03） */
export const RESCUE_CARD_MINUTES = 30
