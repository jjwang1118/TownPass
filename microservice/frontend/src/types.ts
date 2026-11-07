/** 四個吃藥時段（CLAUDE.md：9:00、12:00、18:00、22:00） */
export type SlotKey = 'morning' | 'noon' | 'evening' | 'bedtime'

export type MealTiming = '飯前' | '飯後'

export type SlotStatus = 'past' | 'now' | 'later'

export type Lang = 'zh' | 'nan' // 國語／台語

export interface Medicine {
  /** 藥單徽章，例：A1 */
  code: string
  /** 一次幾顆，0.5 為單位 */
  amount: number
  /** 藥名＋劑量，例：Metformin 500 毫克 */
  name: string
  /** 功效，例：降血糖 */
  effect: string
  /** 服用時段（可複選） */
  slots: SlotKey[]
  meal: MealTiming
}

export interface Prescription {
  /** 藥單分類字母，例：A */
  code: string
  hospital: string
  department: string
  /** 看診日期 YYYY-MM-DD */
  visitDate: string
  /** 給藥天數 */
  days: number
  medicines: Medicine[]
}

export interface Appointment {
  hospital: string
  department: string
  doctor: string
  /** YYYY-MM-DD */
  date: string
  /** HH:mm */
  time: string
  /** 時段顯示文字，例：上午 09:30 */
  timeLabel: string
  number: number
}

export interface Contact {
  name: string
  relation: string
  phone: string
}

export interface EmergencyCard {
  name: string
  /** YYYY/MM/DD */
  birthday: string
  gender: '女' | '男' | ''
  bloodType: 'A' | 'B' | 'O' | 'AB' | '不知道' | ''
  contact1: Contact
  contact2: Contact | null
  chronic: string[]
  drugAllergy: string
  foodAllergy: string
  special: string[]
  hospitalRecord: string
  language: '國語' | '台語' | '客語' | ''
  consent: boolean
  /** YYYY/MM/DD */
  updatedAt: string
}

export interface ViewLog {
  /** ISO 時間 */
  time: string
  viewer: string
}

export interface FamilyMember {
  id: string
  name: string
  relation: string
}

export interface Invite {
  code: string
  /** epoch ms */
  expiresAt: number
}

export interface RescueNotice {
  time: string
  unit: string
  staffId: string
}

export interface RescueSession {
  unit: string
  staffId: string
  /** 查詢開啟醫療卡的時間 epoch ms，用於 30 分鐘自動關閉 */
  openedAt: number | null
}

export interface ElderProfile {
  name: string
  phone: string
  idNumber: string
}

/** 新增藥單流程中的草稿藥品（含核對狀態） */
export interface DraftMedicine extends Medicine {
  checked: boolean
}

export interface DraftPrescription {
  code: string
  hospital: string
  department: string
  visitDate: string
  days: number
  medicines: DraftMedicine[]
}

export interface BookingDraft {
  hospital: string
  department: string
  doctor: string
  date: string
  time: string
}

export interface SelectOption {
  value: string
  label: string
  subtitle?: string
  disabled?: boolean
}

export interface DrugEntry {
  /** 英文藥名 */
  name: string
  /** 中文名 */
  zh?: string
  doses: string[]
  effect: string
  /** 北市聯醫常用藥排前面 */
  common?: boolean
  source: string
}

/** EL-PG-13／EL-PG-14 藥品表單值 */
export type MedicineFormValue = Omit<Medicine, 'code'>
