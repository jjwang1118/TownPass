/**
 * 模擬資料：後端尚未建立，所有資料由此提供。
 * 數值取自各介面規格的「顯示資料」範例。之後串接後端時，替換 services/api.ts 內的實作即可。
 */
import type {
  Appointment,
  DraftPrescription,
  DrugEntry,
  ElderProfile,
  EmergencyCard,
  FamilyMember,
  Prescription,
  RescueNotice,
  SelectOption,
  ViewLog,
} from '@/types'

export const ELDER: ElderProfile = {
  name: '王美玉',
  phone: '0928-111-222',
  idNumber: 'A223456789',
}

/** 預設藥單：測試資料已清空，藥單一律由使用者透過新增藥單流程建立 */
export const PRESCRIPTIONS: Prescription[] = []

export const APPOINTMENT: Appointment = {
  hospital: '仁愛院區',
  department: '心臟科',
  doctor: '林醫師',
  date: '2026-11-14',
  time: '09:30',
  timeLabel: '上午 09:30',
  number: 12,
}

export const EMERGENCY_CARD: EmergencyCard = {
  name: '王美玉',
  birthday: '1948/05/12',
  gender: '女',
  bloodType: 'O',
  contact1: { name: '陳小華', relation: '女兒', phone: '0912-345-678' },
  contact2: { name: '陳大明', relation: '兒子', phone: '0933-222-111' },
  chronic: ['高血壓', '糖尿病'],
  drugAllergy: '盤尼西林',
  foodAllergy: '無',
  special: [],
  hospitalRecord: '仁愛院區｜12345678',
  language: '台語',
  consent: true,
  updatedAt: '2026/11/07',
}

export const VIEW_LOGS: ViewLog[] = [
  { time: '2026-11-07T14:32:00', viewer: '救護人員（臺北市消防局）' },
  { time: '2026-11-07T10:05:00', viewer: '陳小華（女兒）' },
]

export const FAMILY_MEMBERS: FamilyMember[] = [{ id: 'f1', name: '陳小華', relation: '女兒' }]

/** 家屬端登入的模擬帳號（台北通 userinfo 拿不到時使用） */
export const FAMILY_USER = { name: '陳小華', relation: '女兒' }

/** 拍藥袋／掃 QR Code 後的模擬辨識結果（EL-PG-07 顯示資料範例） */
export const RECOGNIZED_PRESCRIPTION: DraftPrescription = {
  code: 'A',
  hospital: '仁愛院區',
  department: '心臟科',
  visitDate: '2026-11-05',
  medicines: [
    { code: 'A1', amount: 1, name: 'Amlodipine 5 毫克', effect: '降血壓', slots: ['morning'], meal: '飯後', quantity: 28, checked: false },
    { code: 'A2', amount: 1, name: 'Aspirin 100 毫克', effect: '預防血栓', slots: ['morning'], meal: '飯後', quantity: 28, checked: false },
    { code: 'A3', amount: 1, name: 'Atorvastatin 20 毫克', effect: '降血脂', slots: ['bedtime'], meal: '飯後', quantity: 28, checked: false },
  ],
}

/** 藥名資料庫（EL-INP-02，正式版需串接藥名資料庫） */
export const DRUGS: DrugEntry[] = [
  { name: 'Aspirin', zh: '阿斯匹靈', doses: ['100 毫克', '300 毫克', '500 毫克'], effect: '預防血栓', common: true, source: '食藥署許可證資料' },
  { name: 'Aspirin 腸溶錠', doses: ['100 毫克'], effect: '預防血栓', common: true, source: '食藥署許可證資料' },
  { name: 'Amlodipine', zh: '脈優', doses: ['5 毫克', '10 毫克'], effect: '降血壓', common: true, source: '北市聯醫常用藥' },
  { name: 'Atorvastatin', zh: '立普妥', doses: ['10 毫克', '20 毫克', '40 毫克'], effect: '降血脂', common: true, source: '北市聯醫常用藥' },
  { name: 'Metformin', zh: '庫魯化', doses: ['500 毫克', '850 毫克'], effect: '降血糖', common: true, source: '北市聯醫常用藥' },
  { name: 'Linagliptin', zh: '糖漸平', doses: ['5 毫克'], effect: '降血糖', common: true, source: '北市聯醫常用藥' },
  { name: 'Losartan', zh: '可悅您', doses: ['50 毫克', '100 毫克'], effect: '降血壓', common: true, source: '北市聯醫常用藥' },
  { name: 'Clopidogrel', zh: '保栓通', doses: ['75 毫克'], effect: '預防血栓', common: true, source: '北市聯醫常用藥' },
  { name: 'Bisoprolol', zh: '康肯', doses: ['1.25 毫克', '5 毫克'], effect: '控制心跳', source: '食藥署許可證資料' },
  { name: 'Glimepiride', zh: '瑪爾胰', doses: ['1 毫克', '2 毫克'], effect: '降血糖', source: '食藥署許可證資料' },
  { name: 'Rosuvastatin', zh: '冠脂妥', doses: ['5 毫克', '10 毫克'], effect: '降血脂', source: '食藥署許可證資料' },
  { name: 'Simvastatin', zh: '素果', doses: ['20 毫克'], effect: '降血脂', source: '食藥署許可證資料' },
  { name: 'Omeprazole', zh: '洛賽克', doses: ['20 毫克'], effect: '保護胃', source: '食藥署許可證資料' },
  { name: 'Acetaminophen', zh: '普拿疼', doses: ['500 毫克'], effect: '止痛退燒', common: true, source: '北市聯醫常用藥' },
  { name: 'Allopurinol', zh: '安樂普利諾', doses: ['100 毫克'], effect: '降尿酸', source: '食藥署許可證資料' },
  { name: 'Furosemide', zh: '來適泄', doses: ['40 毫克'], effect: '利尿', source: '食藥署許可證資料' },
  { name: 'Warfarin', zh: '可化凝', doses: ['1 毫克', '5 毫克'], effect: '抗凝血', source: '食藥署許可證資料' },
]

/** 回診預約（限臺北市立聯合醫院） */
export const HOSPITALS = ['仁愛院區', '中興院區', '和平婦幼院區', '忠孝院區', '陽明院區', '林森中醫昆明院區']

export const DEPARTMENTS: Record<string, string[]> = {
  仁愛院區: ['心臟科', '新陳代謝科', '家醫科', '神經內科', '骨科', '眼科'],
  中興院區: ['心臟科', '新陳代謝科', '家醫科', '骨科'],
  和平婦幼院區: ['家醫科', '新陳代謝科', '婦產科', '小兒科'],
  忠孝院區: ['心臟科', '家醫科', '神經內科', '眼科'],
  陽明院區: ['心臟科', '新陳代謝科', '家醫科'],
  林森中醫昆明院區: ['中醫內科', '中醫針灸科'],
}

interface DoctorDef {
  name: string
  /** 0=週日…6=週六 */
  weekdays: number[]
  full?: boolean
}

const DOCTOR_POOL: DoctorDef[][] = [
  [
    { name: '林醫師', weekdays: [1, 5] },
    { name: '王醫師', weekdays: [2, 4], full: true },
    { name: '張醫師', weekdays: [3] },
  ],
  [
    { name: '陳醫師', weekdays: [1, 3] },
    { name: '李醫師', weekdays: [2, 5] },
  ],
  [
    { name: '黃醫師', weekdays: [4], full: true },
    { name: '吳醫師', weekdays: [1, 2, 5] },
  ],
]

export function doctorsOf(hospital: string, department: string): DoctorDef[] {
  const seed = (HOSPITALS.indexOf(hospital) + department.length) % DOCTOR_POOL.length
  // 範例：仁愛院區 心臟科 → 林醫師、王醫師（本月已額滿）
  if (hospital === '仁愛院區' && department === '心臟科') return DOCTOR_POOL[0]
  return DOCTOR_POOL[seed]
}

const WEEKDAY_ZH = ['日', '一', '二', '三', '四', '五', '六']

export function weekdayText(days: number[]): string {
  return days.map((d) => `週${WEEKDAY_ZH[d]}`).join('、')
}

export const TIME_SLOTS: { time: string; label: string }[] = [
  { time: '09:00', label: '上午 09:00' },
  { time: '09:30', label: '上午 09:30' },
  { time: '10:00', label: '上午 10:00' },
  { time: '10:30', label: '上午 10:30' },
  { time: '11:00', label: '上午 11:00' },
  { time: '14:00', label: '下午 14:00' },
  { time: '14:30', label: '下午 14:30' },
  { time: '15:00', label: '下午 15:00' },
]

/** 每個時段是否額滿（依日期與時間做穩定的模擬結果） */
export function isTimeFull(date: string, time: string): boolean {
  const n = Number(date.slice(-2)) + Number(time.slice(0, 2)) + Number(time.slice(3))
  return n % 5 === 0
}

/** FM-PG-06 範例通知（尚無實際查看紀錄時顯示） */
export const RESCUE_NOTICE_EXAMPLE: RescueNotice = {
  time: '2026-11-07T14:32:00',
  unit: '臺北市政府消防局',
  staffId: 'A12345',
}

/** 救護人員所屬單位 */
export const RESCUE_UNITS: SelectOption[] = [
  '大安分隊',
  '信義分隊',
  '中正分隊',
  '中山分隊',
  '松山分隊',
  '萬華分隊',
  '大同分隊',
  '士林分隊',
  '北投分隊',
  '內湖分隊',
  '南港分隊',
  '文山分隊',
].map((u) => ({ value: `臺北市政府消防局 ${u}`, label: `臺北市政府消防局 ${u}` }))
