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
  /** 領藥總顆數（藥袋上的數量），用來計算還剩幾天：剩下顆數 ÷ 每天吃幾顆 */
  quantity: number
  /** 後端藥品 id（加入藥單後才有） */
  id?: string
  /** 健保藥品代號：藥名搜尋選到、或 QR Code 帶入時才有，用來比對同成分 */
  licenseNo?: string
}

export interface Prescription {
  /** 後端藥單 id */
  id?: string
  /** 藥單分類字母，例：A */
  code: string
  hospital: string
  department: string
  /** 看診（領藥）日期 YYYY-MM-DD，從這天開始吃 */
  visitDate: string
  medicines: Medicine[]
  doctor?: string
  /** 已移到「已吃完」 */
  finished?: boolean
}

export interface Appointment {
  id?: string
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
  /** 救護人員查詢結果只有年齡、沒有出生日期 */
  age?: number | null
  gender: '女' | '男' | ''
  bloodType: 'A' | 'B' | 'O' | 'AB' | '不知道' | ''
  /** 緊急聯絡人（只有一位，UI E14） */
  contact1: Contact
  chronic: string[]
  drugAllergy: string
  foodAllergy: string
  special: string[]
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
}

/** 新增藥單流程中的草稿藥品（含核對狀態） */
export interface DraftMedicine extends Medicine {
  checked: boolean
  /** 拍照辨識沒把握（紅框「電腦不確定這一項」） */
  uncertain?: boolean
}

export interface DraftPrescription {
  code: string
  hospital: string
  department: string
  visitDate: string
  medicines: DraftMedicine[]
  /** 由手動新增建立（非拍照／QR Code 辨識） */
  manual?: boolean
  /** 新增方式（送給後端） */
  source?: 'photo' | 'qr' | 'manual'
  doctor?: string
  /** 給藥天數（QR Code 帶入；藥品沒有總顆數時用） */
  days?: number | null
  /** 同成分警示文字，例：「C1 和 A1：這兩包好像是同一種藥，請問藥師」 */
  warnings?: string[]
}

export interface BookingDraft {
  hospital: string
  department: string
  doctor: string
  /** 門診（後端 session_id） */
  date: string
  /** 看診時間（後端 slot_id） */
  time: string
  /** 選到的項目 id 與顯示文字（後端資料） */
  hospitalId?: string
  departmentId?: string
  doctorId?: string
  dateLabel?: string
  timeLabel?: string
  /** 從哪一張藥單帶入院區與科別 */
  fromLetter?: string
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
  /** 劑量 → 健保藥品代號（後端藥名搜尋） */
  licenses?: Record<string, string>
}

/** EL-PG-13／EL-PG-14 藥品表單值 */
export type MedicineFormValue = Omit<Medicine, 'code'>
