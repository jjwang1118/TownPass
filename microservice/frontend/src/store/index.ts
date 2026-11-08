/**
 * 全域狀態：後端資料的快取，加上畫面流程的暫存（藥單草稿、預約選擇、朗讀語言）。
 *
 * - 藥單、回診預約、緊急醫療卡、家屬綁定、救護人員查詢都從後端讀寫（@/api）。
 * - 只有畫面流程的暫存存在 localStorage，重新整理後仍保留；後端資料每次重新讀取。
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
import { ELDER, FAMILY_USER } from '@/data/mock'
import { ApiError, del, get, getToken, post, put, setToken, type Role } from '@/api/client'
import {
  cardToApi,
  doseToMedicine,
  draftToApi,
  responderCardToCard,
  shortHospital,
  toAppointment,
  toCard,
  toDraft,
  toPrescription,
  toRescueNotices,
  toViewLogs,
} from '@/api/mappers'
import type {
  AppointmentOut,
  BindingOut,
  CardOut,
  ClinicDayOut,
  DepartmentOut,
  DoctorOut,
  HospitalOut,
  InviteOut,
  MeOut,
  PhotoRecognitionIn,
  PrescriptionCreated,
  PrescriptionOut,
  PreviewOut,
  ResponderCardOut,
  ResponderTokenOut,
  SlotOut,
  TokenOut,
} from '@/api/types'
import { getUserInfo } from '@/composables/flutterBridge'
import { toISODate } from '@/utils/date'
import { emptyCard } from '@/utils/card'
import { prescriptionDaysLeft } from '@/utils/supply'

const STORAGE_KEY = 'chiah-ioh-lo-ui-v1'

interface FamilyUserState {
  loggedIn: boolean
  name: string
  relation: string
  /** 是否已綁定長輩 */
  bound: boolean
  /** 長輩用自己的帳號查看綁定的另一位長輩（長輩之間可以互相綁定）；家屬頁面改用長輩的登入 */
  viaElder?: boolean
  /** viaElder 時目前查看的綁定 */
  bindingId?: string
}

interface RescueCardState {
  card: EmergencyCard
  medicines: Medicine[]
}

interface BookingData {
  hospitals: HospitalOut[]
  departments: Record<string, DepartmentOut[]>
  doctors: Record<string, DoctorOut[]>
  sessions: Record<string, ClinicDayOut[]>
  slots: Record<string, SlotOut[]>
}

interface State {
  /** 長者本人，或家屬綁定的長輩 */
  elder: ElderProfile
  elderId: string | null
  /** 吃藥中與已吃完的藥單 */
  prescriptions: Prescription[]
  /** 回診預約（今天以後、未取消） */
  appointments: Appointment[]
  /** 剛完成的那一筆預約（EL-PG-12 預約成功頁顯示） */
  lastBooked: Appointment | null
  card: EmergencyCard
  /** 救命卡卡號（救護人員查詢用）；還沒建立或撤回同意時為 null */
  cardCode: string | null
  viewLogs: ViewLog[]
  families: FamilyMember[]
  /** 長輩綁定的其他長輩（我關心的長輩）；id 為綁定 id */
  caredElders: FamilyMember[]
  invite: Invite
  familyUser: FamilyUserState
  rescue: RescueSession | null
  /** 救護人員查到的醫療卡（30 分鐘後自動關閉並清除） */
  rescueCard: RescueCardState | null
  rescueNotices: RescueNotice[]
  /** CM-SEG-01 目前選中的朗讀語言 */
  lang: Lang
  /** 新增藥單流程草稿 */
  draft: DraftPrescription | null
  /** EL-PG-14 手動新增、尚未併入辨識結果的藥品 */
  manualMedicines: DraftMedicine[]
  booking: BookingDraft
  bookingData: BookingData
  /** 已發送過的提醒（避免重複推播） */
  notified: string[]
  /** 已從後端載入 */
  loaded: { elder: boolean; family: boolean }
  /** 最近一次連線錯誤，畫面上方顯示 */
  apiError: string
}

function emptyBooking(): BookingDraft {
  return { hospital: '', department: '', doctor: '', date: '', time: '' }
}

function defaults(): State {
  return {
    elder: { ...ELDER },
    elderId: null,
    prescriptions: [],
    appointments: [],
    lastBooked: null,
    card: emptyCard(),
    cardCode: null,
    viewLogs: [],
    families: [],
    caredElders: [],
    invite: { code: '', expiresAt: 0 },
    familyUser: { loggedIn: false, name: FAMILY_USER.name, relation: FAMILY_USER.relation, bound: false },
    rescue: null,
    rescueCard: null,
    rescueNotices: [],
    lang: 'zh',
    draft: null,
    manualMedicines: [],
    booking: emptyBooking(),
    bookingData: { hospitals: [], departments: {}, doctors: {}, sessions: {}, slots: {} },
    notified: [],
    loaded: { elder: false, family: false },
    apiError: '',
  }
}

/** 存在瀏覽器的只有畫面流程的暫存 */
const PERSISTED = ['lang', 'draft', 'manualMedicines', 'booking', 'lastBooked', 'notified', 'familyUser', 'rescue'] as const

function load(): State {
  const base = defaults()
  try {
    const saved = JSON.parse(window.localStorage.getItem(STORAGE_KEY) ?? '{}') as Partial<State>
    PERSISTED.forEach((key) => {
      if (saved[key] !== undefined) (base as unknown as Record<string, unknown>)[key] = saved[key]
    })
    if (base.lang !== 'en') base.lang = 'zh' // 舊版存過的「台語」（nan）改回國語
  } catch {
    /* 讀取失敗時用預設值 */
  }
  return base
}

export const state = reactive<State>(load())

watch(
  () => PERSISTED.map((key) => state[key]),
  () => {
    try {
      const data = Object.fromEntries(PERSISTED.map((key) => [key, state[key]]))
      window.localStorage.setItem(STORAGE_KEY, JSON.stringify(data))
    } catch {
      /* 無痕模式或儲存被封鎖時忽略 */
    }
  },
  { deep: true },
)

/** 執行後端呼叫；連不到伺服器時在畫面上方顯示錯誤 */
async function call<T>(fn: () => Promise<T>): Promise<T> {
  try {
    const result = await fn()
    state.apiError = ''
    return result
  } catch (e) {
    if (e instanceof ApiError && e.code === 'NETWORK') state.apiError = e.message
    throw e
  }
}

const elderPath = (path = '') => `/elders/${state.elderId}${path}`

/* ---------- 登入（台北通） ---------- */

/** 瀏覽器沒有台北通 App 時使用的模擬帳號（格式同 assets/mock_data/account.json） */
function mockAccount(role: 'elder' | 'family') {
  const elder = role === 'elder'
  return {
    id: elder ? 'demo-elder' : 'demo-family',
    account: elder ? 'demo-elder' : 'demo-family',
    username: elder ? 'Meiyu' : 'Xiaohua',
    realName: elder ? '王美玉' : FAMILY_USER.name,
    idNo: elder ? 'A223456789' : 'A234567890',
    email: elder ? 'elder@example.com' : 'family@example.com',
    phoneNo: elder ? '0928111222' : '0912345678',
    birthday: elder ? '1948/05/12' : '1978/03/02',
    memberType: 'personal',
    verifyLevel: '3',
    addresses: [],
    residentAddress: '臺北市大安區',
    citizen: true,
    nativePeople: false,
    cityInternetUid: '',
  }
}

/** 用台北通帳號登入，第一次使用時設定身分 */
async function loginTownpass(role: 'elder' | 'family'): Promise<MeOut> {
  const account = (await getUserInfo()) ?? mockAccount(role)
  const res = await post<TokenOut>('/auth/townpass', { name: 'userinfo', data: account })
  setToken(role, res.access_token)
  if (res.user.role !== role) await put('/me/role', { role }, { role })
  return { ...res.user, role }
}

async function me(role: 'elder' | 'family'): Promise<MeOut> {
  if (getToken(role)) {
    try {
      return await get<MeOut>('/me', { role })
    } catch (e) {
      if (!(e instanceof ApiError) || e.status !== 401) throw e
    }
  }
  return loginTownpass(role)
}

/* ---------- 長者 ---------- */

/** 進入長者頁面前呼叫：登入並載入資料。force 時重新讀取。 */
export async function ensureElder(force = false): Promise<void> {
  if (state.loaded.elder && !force) return
  try {
    await call(async () => {
      // 每次開啟都用台北通 userinfo 重新登入：更新姓名、電話與身分證字號雜湊（救護人員以身分證字號查詢）
      const user = await loginTownpass('elder')
      state.elderId = user.id
      state.elder = { name: user.real_name, phone: '' }
      await refreshElder()
      state.loaded.elder = true
    })
  } catch (e) {
    if (!state.apiError) state.apiError = e instanceof Error ? e.message : String(e)
  }
}

async function refreshElder(): Promise<void> {
  await Promise.all([refreshPrescriptions('elder'), refreshAppointments('elder'), refreshCard('elder'), refreshFamilies()])
}

async function refreshPrescriptions(role: Role): Promise<void> {
  const [active, finished] = await Promise.all([
    get<PrescriptionOut[]>(elderPath('/prescriptions'), { role, query: { status: 'active' } }),
    get<PrescriptionOut[]>(elderPath('/prescriptions'), { role, query: { status: 'finished' } }),
  ])
  state.prescriptions = [...active, ...finished].map(toPrescription)
}

async function refreshAppointments(role: Role): Promise<void> {
  const list = await get<AppointmentOut[]>(elderPath('/appointments'), { role })
  state.appointments = list.map(toAppointment)
}

async function refreshCard(role: Role): Promise<void> {
  try {
    const card = await get<CardOut>(elderPath('/emergency-card'), { role })
    state.card = toCard(card)
    state.cardCode = card.code?.code ?? null
    state.viewLogs = toViewLogs(card)
    state.rescueNotices = toRescueNotices(card)
  } catch (e) {
    if (!(e instanceof ApiError) || e.code !== 'CARD_NOT_CREATED') throw e
    state.card = emptyCard()
    state.cardCode = null
    state.viewLogs = []
    state.rescueNotices = []
  }
}

/** 綁定清單同時有「我邀請的」（我是 elder_id）與「我去綁定的」（我是 family_id） */
async function refreshFamilies(): Promise<void> {
  const bindings = await get<BindingOut[]>('/family/bindings', { role: 'elder' })
  const self = state.elderId
  state.families = bindings
    .filter((b) => b.elder_id === self)
    .map((b) => ({ id: b.id, name: b.family_name, relation: b.relation_label }))
  state.caredElders = bindings
    .filter((b) => b.family_id === self)
    .map((b) => ({ id: b.id, name: b.elder_name, relation: b.relation_label }))
}

/* ---------- 藥單 ---------- */

/** 藥單還剩幾天 = 剩下顆數 ÷ 每天吃幾顆（取最晚吃完的藥），詳見 utils/supply.ts */
export function daysLeft(rx: Prescription, now: Date): number {
  return prescriptionDaysLeft(rx, now)
}

export function isFinished(rx: Prescription, now: Date): boolean {
  return !!rx.finished || daysLeft(rx, now) <= 0
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

/** 下一張藥單的字母（手動新增的預覽用；實際字母由後端加入時配發） */
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

/** 辨識結果（QR、拍照）建立草稿，併入 EL-PG-14 手動新增的藥品 */
function setDraftFromPreview(preview: PreviewOut) {
  const draft = toDraft(preview)
  const manual = state.manualMedicines.map((m) => ({ ...m, checked: false }))
  state.draft = { ...draft, medicines: recode([...draft.medicines, ...manual], draft.code) }
  state.manualMedicines = []
}

/** EL-PG-06 掃藥袋 QR Code：交給後端解析（格式見 docs/qrcode_format.md），失敗時丟出 ApiError */
export async function startDraftFromQr(raw: string): Promise<void> {
  const preview = await call(() =>
    post<PreviewOut>(elderPath('/prescriptions/qr-preview'), { name: 'qr_code_scan', data: raw }, { role: 'elder' }),
  )
  setDraftFromPreview(preview)
}

/** 拍照或相簿 OCR 整理的欄位送後端比對；預覽不儲存，核對後才加入藥單。 */
export async function startDraftFromRecognition(recognized: PhotoRecognitionIn, signal?: AbortSignal) {
  const preview = await call(() => post<PreviewOut>(elderPath('/prescriptions/photo-preview'), recognized, { role: 'elder', signal }))
  if (!signal?.aborted) setDraftFromPreview(preview)
}

export function addManualMedicine(med: Omit<DraftMedicine, 'code' | 'checked'>) {
  state.manualMedicines.push({ ...med, code: '', checked: false })
}

/** 手動新增藥品 →「已輸入」確認 → 以手動輸入的藥品建立藥單草稿（院區／科別未知，標示為手動新增） */
export function startDraftFromManual(med: Omit<DraftMedicine, 'code' | 'checked'>, appendToDraft = false) {
  addManualMedicine(med)
  const added = state.manualMedicines.map((m) => ({ ...m, checked: false }))
  state.manualMedicines = []
  // 從確認藥單頁「再新增一個藥」進來 → 接在原本的手動藥單後面
  if (appendToDraft && state.draft?.manual) {
    state.draft.medicines = recode([...state.draft.medicines, ...added], state.draft.code)
    return
  }
  const now = new Date()
  const code = nextPrescriptionCode(now)
  state.draft = {
    code,
    manual: true,
    source: 'manual',
    hospital: '手動新增',
    department: '',
    visitDate: toISODate(now),
    medicines: recode(added, code),
  }
}

export function updateDraftMedicine(index: number, med: Omit<DraftMedicine, 'code' | 'checked'>) {
  const draft = state.draft
  if (!draft || !draft.medicines[index]) return
  const prev = draft.medicines[index]
  draft.medicines[index] = { ...prev, ...med, uncertain: false }
}

/** EL-PG-08 確認無誤 → 加入藥單（後端配字母、記錄核對者）；回傳同成分警示 */
export async function commitDraft(): Promise<PrescriptionCreated | null> {
  const draft = state.draft
  if (!draft) return null
  const created = await call(() =>
    post<PrescriptionCreated>(elderPath('/prescriptions'), draftToApi(draft), { role: 'elder' }),
  )
  state.draft = null
  await refreshPrescriptions('elder')
  return created
}

/* ---------- 回診預約 ---------- */

export const BOOKING_FIELDS = ['hospital', 'department', 'doctor', 'date', 'time'] as const
export type BookingField = (typeof BOOKING_FIELDS)[number]

/** 欄位相依（UI E10）：院區 → 科別 → 醫師 → 日期 → 時段，依序啟用；換前一項時清空後面的選擇 */
const BOOKING_DEPENDENTS: Record<BookingField, BookingField[]> = {
  hospital: ['department', 'doctor', 'date', 'time'],
  department: ['doctor', 'date', 'time'],
  doctor: ['date', 'time'],
  date: ['time'],
  time: [],
}

const ID_KEY: Partial<Record<BookingField, keyof BookingDraft>> = {
  hospital: 'hospitalId',
  department: 'departmentId',
  doctor: 'doctorId',
}

export function resetBooking(prefill?: Partial<BookingDraft>) {
  state.booking = { ...emptyBooking(), ...prefill }
}

/** 這一欄要先選好哪一欄 */
export function bookingPrerequisite(field: BookingField): BookingField | null {
  const index = BOOKING_FIELDS.indexOf(field)
  return index > 0 ? BOOKING_FIELDS[index - 1] : null
}

/** 選擇某一欄：value 為後端 id（日期是門診、時段是看診時間），label 為顯示文字 */
export function setBookingField(field: BookingField, value: string, label = '') {
  const b = state.booking
  if (field === 'date' || field === 'time') {
    if (b[field] === value) return
    b[field] = value
    if (field === 'date') b.dateLabel = label
    else b.timeLabel = label
  } else {
    const idKey = ID_KEY[field] as 'hospitalId' | 'departmentId' | 'doctorId'
    if (b[idKey] === value && b[field]) return
    b[idKey] = value || undefined
    b[field] = label
  }
  BOOKING_DEPENDENTS[field].forEach((f) => {
    b[f] = ''
    if (f === 'date') b.dateLabel = ''
    if (f === 'time') b.timeLabel = ''
    const key = ID_KEY[f]
    if (key) (b as unknown as Record<string, unknown>)[key] = undefined
  })
}

export function isBookingComplete(): boolean {
  return BOOKING_FIELDS.every((f) => state.booking[f] !== '')
}

/** 讀取某一欄的選項（依前一欄的選擇）；時段每次重新讀取，名額才是即時的 */
export async function loadBookingOptions(field: BookingField): Promise<void> {
  const b = state.booking
  const data = state.bookingData
  const elder = state.elderId ?? undefined
  await call(async () => {
    switch (field) {
      case 'hospital':
        if (!data.hospitals.length) data.hospitals = await get<HospitalOut[]>('/hospitals', { role: 'elder' })
        break
      case 'department':
        if (b.hospitalId)
          data.departments[b.hospitalId] = await get<DepartmentOut[]>(`/hospitals/${b.hospitalId}/departments`, {
            role: 'elder',
            query: { elder_id: elder },
          })
        break
      case 'doctor':
        if (b.departmentId)
          data.doctors[b.departmentId] = await get<DoctorOut[]>(`/departments/${b.departmentId}/doctors`, {
            role: 'elder',
            query: { elder_id: elder },
          })
        break
      case 'date':
        if (b.doctorId) data.sessions[b.doctorId] = await get<ClinicDayOut[]>(`/doctors/${b.doctorId}/sessions`, { role: 'elder' })
        break
      case 'time':
        if (b.date) data.slots[b.date] = await get<SlotOut[]>(`/sessions/${b.date}/slots`, { role: 'elder' })
        break
    }
  })
}

/** EL-PG-09：從吃藥中的藥單帶入院區與科別（院區屬於聯合醫院時） */
export async function prefillBooking(): Promise<Prescription | null> {
  await loadBookingOptions('hospital')
  for (const rx of activePrescriptions(new Date())) {
    const hospital = state.bookingData.hospitals.find((h) => shortHospital(h.name) === rx.hospital)
    if (!hospital) continue
    setBookingField('hospital', hospital.id, shortHospital(hospital.name))
    await loadBookingOptions('department')
    const department = state.bookingData.departments[hospital.id]?.find((d) => d.name === rx.department)
    if (department) setBookingField('department', department.id, department.name)
    state.booking.fromLetter = rx.code
    return rx
  }
  return null
}

/** EL-PG-11 確認預約；名額已滿等狀況丟出 ApiError（message 可直接顯示） */
export async function confirmBooking(): Promise<Appointment> {
  const created = await call(() =>
    post<AppointmentOut>(elderPath('/appointments'), { slot_id: state.booking.time }, { role: 'elder' }),
  )
  const appt = toAppointment(created)
  state.lastBooked = appt
  await refreshAppointments('elder')
  return appt
}

export function appointmentTime(a: Appointment): Date {
  const [y, mo, d] = a.date.split('-').map(Number)
  const [h, m] = a.time.split(':').map(Number)
  return new Date(y, mo - 1, d, h, m)
}

/** 尚未到的所有回診預約，依時間先後排序 */
export function upcomingAppointments(now: Date): Appointment[] {
  return state.appointments
    .filter((a) => appointmentTime(a).getTime() >= now.getTime())
    .sort((a, b) => appointmentTime(a).getTime() - appointmentTime(b).getTime())
}

/* ---------- 緊急醫療卡 ---------- */

/** 儲存（第一次會先記錄健康資料同意）；格式錯誤等狀況丟出 ApiError */
export async function saveCard(card: EmergencyCard): Promise<void> {
  await call(async () => {
    if (!state.card.consent) await post(elderPath('/consents'), {}, { role: 'elder' })
    await put(elderPath('/emergency-card'), cardToApi(card), { role: 'elder' })
    await refreshCard('elder')
  })
}

/* ---------- 邀請家屬 ---------- */

export async function regenerateInvite(): Promise<void> {
  const invite = await call(() => post<InviteOut>('/family/invites', {}, { role: 'elder' }))
  state.invite = { code: invite.code, expiresAt: Date.parse(invite.expires_at) }
}

export async function ensureInviteValid(): Promise<void> {
  if (!state.invite.code || state.invite.expiresAt <= Date.now()) await regenerateInvite()
}

export async function unbindFamily(id: string): Promise<void> {
  await call(() => del(`/family/bindings/${id}`, { role: 'elder' }))
  await refreshFamilies()
}

export type ElderBindResult = 'ok' | 'self' | 'invalid'

/** 長輩用自己的帳號輸入另一位長輩的邀請碼（長輩之間可以互相綁定，但不能綁定自己） */
export async function bindAsElder(code: string): Promise<ElderBindResult> {
  try {
    await call(() => post('/family/bindings', { code, relation_label: '親友' }, { role: 'elder' }))
  } catch (e) {
    if (e instanceof ApiError && e.code === 'SELF_BIND') return 'self'
    if (e instanceof ApiError && e.code !== 'NETWORK') return 'invalid'
    throw e
  }
  await refreshFamilies()
  return 'ok'
}

/** 長輩查看綁定的另一位長輩：沿用家屬頁面（FM-PG-03～05），改用長輩自己的登入 */
export function viewCaredElder(bindingId: string): void {
  Object.assign(state.familyUser, { loggedIn: true, bound: true, viaElder: true, bindingId })
  state.loaded.family = false
  // 長者本人的資料會被覆蓋，回到長者頁面時重新讀取
  state.loaded.elder = false
}

/* ---------- 家屬端 ---------- */

/** 家屬頁面使用的登入：家屬帳號，或長輩查看綁定的長輩時用長輩帳號 */
const viewerRole = (): Role => (state.familyUser.viaElder ? 'elder' : 'family')

async function refreshFamily(): Promise<void> {
  const role = viewerRole()
  const bindings = await get<BindingOut[]>('/family/bindings', { role })
  const binding = state.familyUser.viaElder
    ? bindings.find((b) => b.id === state.familyUser.bindingId)
    : bindings[0]
  state.familyUser.bound = !!binding
  if (!binding) return
  state.elderId = binding.elder_id
  state.elder = { name: binding.elder_name, phone: binding.elder_phone }
  await Promise.all([refreshPrescriptions(role), refreshAppointments(role), refreshCard(role)])
}

/** FM-PG-01 用台北通帳號登入（瀏覽器使用模擬帳號） */
export async function familyLogin(): Promise<void> {
  await call(async () => {
    const user = await me('family')
    Object.assign(state.familyUser, { loggedIn: true, name: user.real_name, viaElder: false, bindingId: undefined })
    await refreshFamily()
    state.loaded.family = true
  })
}

/** 進入家屬頁面前呼叫：已登入過就重新讀取長輩的資料 */
export async function ensureFamily(force = false): Promise<void> {
  if (!state.familyUser.loggedIn || !getToken(viewerRole())) {
    state.familyUser.loggedIn = false
    return
  }
  if (state.loaded.family && !force) return
  try {
    await call(refreshFamily)
    state.loaded.family = true
  } catch (e) {
    if (e instanceof ApiError && e.status === 401) state.familyUser.loggedIn = false
    else if (!state.apiError) state.apiError = e instanceof Error ? e.message : String(e)
  }
}

/** FM-PG-02 綁定：邀請碼正確且未過期才成功 */
export async function bindWithInviteCode(code: string): Promise<boolean> {
  try {
    await call(() =>
      post('/family/bindings', { code, relation_label: state.familyUser.relation || '家人' }, { role: 'family' }),
    )
  } catch (e) {
    if (e instanceof ApiError && e.code !== 'NETWORK') return false
    throw e
  }
  await refreshFamily()
  return true
}

/* ---------- 救護人員端 ---------- */

/** RE-PG-01 登入（所屬單位＋人員編號＋密碼，比對消防局名冊）；失敗時丟出 ApiError */
export async function rescueLogin(unit: string, staffId: string, password: string): Promise<void> {
  const res = await call(() =>
    post<ResponderTokenOut>('/responder/login', {
      unit: unit.replace('臺北市政府消防局', '').trim(),
      staff_no: staffId,
      password,
    }),
  )
  setToken('rescue', res.access_token)
  state.rescue = { unit, staffId: res.staff_no, openedAt: null }
}

/**
 * RE-PG-02 查詢：輸入救命卡卡號或在 App 內掃卡片 QR Code（不使用身分證字號）。
 * 成功時後端會記錄查看紀錄並通知家屬；查無資料回傳 false。
 */
/** RE-PG-02 查詢：長者身分證字號（主要），或在 App 內掃救命卡 QR */
export async function rescueSearch(input: { idNo?: string; qr?: string }): Promise<boolean> {
  if (!state.rescue) return false
  const body = input.qr ? { qr: { name: 'qr_code_scan', data: input.qr } } : { id_no: input.idNo }
  try {
    const result = await call(() => post<ResponderCardOut>('/responder/cards/lookup', body, { role: 'rescue' }))
    state.rescueCard = {
      card: responderCardToCard(result),
      medicines: result.current_medications.map(doseToMedicine),
    }
    state.rescue.openedAt = Date.now()
    return true
  } catch (e) {
    if (e instanceof ApiError && ['CARD_NOT_FOUND', 'CARD_CODE_INVALID', 'ID_NO_INVALID', 'VALIDATION_ERROR'].includes(e.code))
      return false
    if (e instanceof ApiError && e.status === 401) state.rescue = null
    throw e
  }
}

export function closeRescueCard() {
  state.rescueCard = null
  if (state.rescue) state.rescue.openedAt = null
}
