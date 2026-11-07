/**
 * 全域狀態（模擬後端）。資料存在 localStorage 讓重新整理後仍保留，讀寫失敗時退回預設值。
 * 正式版串接後端時，各 action 改為呼叫 API。
 */
import { reactive, watch } from 'vue'
import type {
  Appointment,
  BookingDraft,
  DraftMedicine,
  DraftPrescription,
  ElderProfile,
  EmergencyCard,
  FamilyMember,
  Invite,
  Lang,
  Medicine,
  Prescription,
  RescueNotice,
  RescueSession,
  ViewLog,
} from '@/types'
import {
  APPOINTMENT,
  ELDER,
  EMERGENCY_CARD,
  FAMILY_MEMBERS,
  FAMILY_USER,
  PRESCRIPTIONS,
  RECOGNIZED_PRESCRIPTION,
  VIEW_LOGS,
} from '@/data/mock'
import { INVITE_VALID_MINUTES } from '@/data/constants'
import { parseDate, toISODate } from '@/utils/date'
import { dailyAmount, prescriptionDaysLeft } from '@/utils/supply'

const STORAGE_KEY = 'yaobao-pingan-state-v1'

interface FamilyUserState {
  loggedIn: boolean
  name: string
  relation: string
  /** 是否已綁定長輩（模擬：目前只有一位長輩 王美玉） */
  bound: boolean
}

interface State {
  elder: ElderProfile
  prescriptions: Prescription[]
  appointment: Appointment | null
  card: EmergencyCard
  viewLogs: ViewLog[]
  families: FamilyMember[]
  invite: Invite
  familyUser: FamilyUserState
  rescue: RescueSession | null
  rescueNotices: RescueNotice[]
  /** CM-SEG-01 目前選中的朗讀語言 */
  lang: Lang
  /** 新增藥單流程草稿 */
  draft: DraftPrescription | null
  /** EL-PG-14 手動新增、尚未併入辨識結果的藥品 */
  manualMedicines: DraftMedicine[]
  booking: BookingDraft
  /** 已發送過的提醒（避免重複推播） */
  notified: string[]
  /** 存檔資料版本；舊版存檔載入時依版本清理資料 */
  dataVersion: number
}

/**
 * 目前存檔資料版本
 * - 4：清空先前存下的測試藥單
 */
const DATA_VERSION = 4

const clone = <T>(v: T): T => JSON.parse(JSON.stringify(v)) as T

function newInviteCode(): Invite {
  const code = String(Math.floor(Math.random() * 1_000_000)).padStart(6, '0')
  return { code, expiresAt: Date.now() + INVITE_VALID_MINUTES * 60_000 }
}

function emptyBooking(): BookingDraft {
  return { hospital: '', department: '', doctor: '', date: '', time: '' }
}

function defaults(): State {
  return {
    elder: clone(ELDER),
    prescriptions: clone(PRESCRIPTIONS),
    appointment: clone(APPOINTMENT),
    card: clone(EMERGENCY_CARD),
    viewLogs: clone(VIEW_LOGS),
    families: clone(FAMILY_MEMBERS),
    invite: { code: '483921', expiresAt: Date.now() + INVITE_VALID_MINUTES * 60_000 },
    familyUser: { loggedIn: false, name: FAMILY_USER.name, relation: FAMILY_USER.relation, bound: false },
    rescue: null,
    rescueNotices: [],
    lang: 'zh',
    draft: null,
    manualMedicines: [],
    booking: emptyBooking(),
    notified: [],
    dataVersion: DATA_VERSION,
  }
}

/** 舊版存檔以「給藥天數 days」記錄，轉成每個藥的總顆數（天數 × 每天吃幾顆） */
function migrateQuantity<T extends { medicines: Medicine[]; days?: number }>(rx: T): T {
  const days = rx.days ?? 28
  rx.medicines.forEach((m) => {
    if (typeof m.quantity !== 'number' || Number.isNaN(m.quantity)) m.quantity = days * dailyAmount(m)
  })
  delete rx.days
  return rx
}

function load(): State {
  const base = defaults()
  try {
    const raw = window.localStorage.getItem(STORAGE_KEY)
    if (!raw) return base
    const parsed = JSON.parse(raw) as Partial<State>
    const saved = { ...base, ...parsed }
    // v4：清空舊存檔裡的測試藥單（含未完成的新增草稿與暫存的手動藥品）
    if ((parsed.dataVersion ?? 1) < DATA_VERSION) {
      saved.prescriptions = []
      saved.draft = null
      saved.manualMedicines = []
      saved.notified = saved.notified.filter((k) => !k.startsWith('slot:'))
    }
    saved.dataVersion = DATA_VERSION
    saved.prescriptions.forEach(migrateQuantity)
    if (saved.draft) migrateQuantity(saved.draft)
    saved.manualMedicines.forEach((m) => {
      if (typeof m.quantity !== 'number') m.quantity = 28 * dailyAmount(m)
    })
    return saved
  } catch {
    return base
  }
}

export const state = reactive<State>(load())

watch(
  state,
  (s) => {
    try {
      window.localStorage.setItem(STORAGE_KEY, JSON.stringify(s))
    } catch {
      /* 無痕模式或儲存被封鎖時忽略 */
    }
  },
  { deep: true },
)

/* ---------- 藥單 ---------- */

/** 藥單還剩幾天 = 剩下顆數 ÷ 每天吃幾顆（取最晚吃完的藥），詳見 utils/supply.ts */
export function daysLeft(rx: Prescription, now: Date): number {
  return prescriptionDaysLeft(rx, now)
}

export function isFinished(rx: Prescription, now: Date): boolean {
  return daysLeft(rx, now) <= 0
}

export function activePrescriptions(now: Date): Prescription[] {
  return state.prescriptions.filter((rx) => !isFinished(rx, now))
}

export interface MedicineWithRx extends Medicine {
  rx: Prescription
}

export function activeMedicines(now: Date): MedicineWithRx[] {
  return activePrescriptions(now).flatMap((rx) => rx.medicines.map((m) => ({ ...m, rx })))
}

/** 下一張藥單的字母：活動中藥單沒用到的第一個字母 */
function nextPrescriptionCode(now: Date): string {
  const used = new Set(activePrescriptions(now).map((rx) => rx.code))
  for (let i = 0; i < 26; i += 1) {
    const c = String.fromCharCode(65 + i)
    if (!used.has(c)) return c
  }
  return 'Z'
}

function recode(medicines: DraftMedicine[], code: string): DraftMedicine[] {
  return medicines.map((m, i) => ({ ...m, code: `${code}${i + 1}` }))
}

/** EL-PG-05／EL-PG-06 辨識完成 → 建立草稿（併入 EL-PG-14 手動新增的藥品） */
export function startDraftFromRecognition(recognized: DraftPrescription = RECOGNIZED_PRESCRIPTION) {
  const code = nextPrescriptionCode(new Date())
  const medicines = [...clone(recognized.medicines), ...clone(state.manualMedicines)].map((m) => ({
    ...m,
    checked: false,
  }))
  state.draft = { ...clone(recognized), code, medicines: recode(medicines, code) }
  state.manualMedicines = []
}

export function addManualMedicine(med: Omit<DraftMedicine, 'code' | 'checked'>) {
  state.manualMedicines.push({ ...med, code: '', checked: false })
}

/** 手動新增藥品 →「已輸入」確認 → 以手動輸入的藥品建立藥單草稿（院區／科別未知，標示為手動新增） */
export function startDraftFromManual(med: Omit<DraftMedicine, 'code' | 'checked'>, appendToDraft = false) {
  addManualMedicine(med)
  const added = clone(state.manualMedicines).map((m) => ({ ...m, checked: false }))
  state.manualMedicines = []
  // 從確認藥單頁「再新增一個藥」進來 → 接在原本的手動藥單後面
  if (appendToDraft && state.draft?.manual) {
    state.draft.medicines = recode([...state.draft.medicines, ...added], state.draft.code)
    return
  }
  const now = new Date()
  const code = nextPrescriptionCode(now)
  const medicines = added
  state.draft = {
    code,
    manual: true,
    hospital: '手動新增',
    department: '',
    visitDate: toISODate(now),
    medicines: recode(medicines, code),
  }
}

export function updateDraftMedicine(index: number, med: Omit<DraftMedicine, 'code' | 'checked'>) {
  const draft = state.draft
  if (!draft || !draft.medicines[index]) return
  const prev = draft.medicines[index]
  draft.medicines[index] = { ...prev, ...med }
}

/** EL-PG-08 確認無誤 → 加入藥單 */
export function commitDraft() {
  const draft = state.draft
  if (!draft) return
  const rx: Prescription = {
    code: draft.code,
    hospital: draft.hospital,
    department: draft.department,
    visitDate: draft.visitDate,
    medicines: draft.medicines.map(({ checked: _checked, ...m }) => m),
  }
  state.prescriptions.push(rx)
  state.draft = null
}

/* ---------- 回診預約 ---------- */

export const BOOKING_FIELDS = ['hospital', 'department', 'doctor', 'date', 'time'] as const
export type BookingField = (typeof BOOKING_FIELDS)[number]

export function resetBooking(prefill?: Partial<BookingDraft>) {
  state.booking = { ...emptyBooking(), ...prefill }
}

/** 選擇某欄後，其後欄位清空（依序鎖定） */
export function setBookingField(field: BookingField, value: string) {
  const idx = BOOKING_FIELDS.indexOf(field)
  if (state.booking[field] === value) return
  state.booking[field] = value
  BOOKING_FIELDS.slice(idx + 1).forEach((f) => {
    state.booking[f] = ''
  })
}

export function isBookingComplete(): boolean {
  return BOOKING_FIELDS.every((f) => state.booking[f] !== '')
}

export function confirmBooking(timeLabel: string): Appointment {
  const b = state.booking
  const appt: Appointment = {
    hospital: b.hospital,
    department: b.department,
    doctor: b.doctor,
    date: b.date,
    time: b.time,
    timeLabel,
    number: 12 + (Number(b.date.slice(-2)) % 20),
  }
  state.appointment = appt
  // 新預約要重新提醒
  state.notified = state.notified.filter((k) => !k.startsWith('appt:'))
  return appt
}

export function upcomingAppointment(now: Date): Appointment | null {
  const a = state.appointment
  if (!a) return null
  const at = parseDate(a.date)
  const [h, m] = a.time.split(':').map(Number)
  at.setHours(h, m)
  return at.getTime() >= now.getTime() ? a : null
}

/* ---------- 緊急醫療卡 ---------- */

export function saveCard(card: EmergencyCard) {
  state.card = { ...clone(card), updatedAt: toISODate(new Date()).replace(/-/g, '/') }
}

/* ---------- 邀請家屬 ---------- */

export function regenerateInvite() {
  state.invite = newInviteCode()
}

export function ensureInviteValid() {
  if (state.invite.expiresAt <= Date.now()) regenerateInvite()
}

export function unbindFamily(id: string) {
  const member = state.families.find((f) => f.id === id)
  state.families = state.families.filter((f) => f.id !== id)
  if (member && member.name === state.familyUser.name) state.familyUser.bound = false
}

/* ---------- 家屬端 ---------- */

export function familyLogin(name?: string) {
  state.familyUser.loggedIn = true
  if (name) state.familyUser.name = name
  // 長者端已綁定此家屬時，視為已綁定
  if (state.families.some((f) => f.name === state.familyUser.name)) state.familyUser.bound = true
}

/** FM-PG-02 綁定：邀請碼正確且未過期才成功 */
export function bindWithInviteCode(code: string): boolean {
  if (code !== state.invite.code || state.invite.expiresAt <= Date.now()) return false
  state.familyUser.bound = true
  if (!state.families.some((f) => f.name === state.familyUser.name)) {
    state.families.push({
      id: `f${Date.now()}`,
      name: state.familyUser.name,
      relation: state.familyUser.relation,
    })
  }
  return true
}

/* ---------- 救護人員端 ---------- */

export function rescueLogin(unit: string, staffId: string) {
  state.rescue = { unit, staffId, openedAt: null }
}

/** RE-PG-02 查詢；成功時記錄查看紀錄並通知家屬 */
export function rescueSearch(idNumber: string): boolean {
  if (!state.rescue) return false
  if (idNumber.toUpperCase() !== state.elder.idNumber) return false
  const nowIso = new Date().toISOString()
  state.rescue.openedAt = Date.now()
  const unitShort = state.rescue.unit.split(' ')[0] ?? state.rescue.unit
  state.viewLogs.unshift({ time: nowIso, viewer: `救護人員（${unitShort.replace('政府', '')}）` })
  state.rescueNotices.unshift({ time: nowIso, unit: state.rescue.unit, staffId: state.rescue.staffId })
  return true
}

export function closeRescueCard() {
  if (state.rescue) state.rescue.openedAt = null
}
