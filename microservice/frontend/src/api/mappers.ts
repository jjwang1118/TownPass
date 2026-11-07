/** 後端資料 ↔ 前端型別。畫面元件只用前端型別（@/types），不直接碰後端格式。 */
import type {
  Appointment,
  DraftMedicine,
  DraftPrescription,
  DrugEntry,
  EmergencyCard,
  Medicine,
  Prescription,
  RescueNotice,
  ViewLog,
} from '@/types'
import { dailyAmount } from '@/utils/supply'
import type {
  AppointmentOut,
  CardOut,
  DoseItemApi,
  DrugSearchItem,
  PrescriptionDraftApi,
  PrescriptionOut,
  PreviewOut,
  ResponderCardOut,
} from './types'

const HOSPITAL_PREFIX = '臺北市立聯合醫院'
const DEFAULT_DAYS = 28

/** 「臺北市立聯合醫院仁愛院區」→「仁愛院區」 */
export const shortHospital = (name: string | null | undefined) => (name ?? '').replace(HOSPITAL_PREFIX, '')

const toMeal = (m: string): Medicine['meal'] => (m === 'before' ? '飯前' : '飯後')
const fromMeal = (m: Medicine['meal']) => (m === '飯前' ? 'before' : 'after')
const isoToSlash = (iso: string | null | undefined) => (iso ? iso.slice(0, 10).replace(/-/g, '/') : '')

/* ---------- 藥單 ---------- */

export function toPrescription(p: PrescriptionOut): Prescription {
  return {
    id: p.id,
    code: p.letter,
    hospital: shortHospital(p.hospital) || '手動新增',
    department: p.department ?? '',
    doctor: p.doctor ?? undefined,
    visitDate: p.visit_date,
    finished: p.status === 'finished',
    medicines: p.medications
      .filter((m) => m.status === 'active')
      .map((m) => {
        const slots = m.slots.map((s) => s.slot_key)
        return {
          id: m.id,
          code: m.code,
          amount: m.dose_qty,
          name: m.name,
          effect: m.purpose ?? '',
          slots,
          meal: toMeal(m.meal_timing),
          quantity: m.quantity ?? (p.days ?? DEFAULT_DAYS) * dailyAmount({ amount: m.dose_qty, slots }),
          licenseNo: m.license_no ?? undefined,
          speechEn: m.speech_text_en || undefined,
        }
      }),
  }
}

/** 預覽結果（QR、拍照）→ 確認藥單的草稿 */
export function toDraft(preview: PreviewOut): DraftPrescription {
  const d = preview.draft
  return {
    code: preview.letter,
    source: d.source,
    manual: d.source === 'manual',
    hospital: shortHospital(d.hospital) || (d.source === 'manual' ? '手動新增' : ''),
    department: d.department ?? '',
    doctor: d.doctor ?? undefined,
    visitDate: d.visit_date,
    days: d.days ?? null,
    warnings: preview.warnings.map((w) => `${w.code} 和 ${w.with_code}：${w.message}`),
    medicines: d.items.map((item, i): DraftMedicine => ({
      code: preview.items[i]?.code ?? `${preview.letter}${i + 1}`,
      name: item.name,
      effect: item.purpose ?? '',
      amount: item.dose_qty,
      slots: item.slots,
      meal: toMeal(item.meal_timing),
      quantity: item.quantity ?? (d.days ?? DEFAULT_DAYS) * dailyAmount({ amount: item.dose_qty, slots: item.slots }),
      licenseNo: item.license_no ?? undefined,
      checked: false,
      uncertain: preview.items[i]?.uncertain ?? false,
    })),
  }
}

/** 確認藥單的草稿 → 送給後端加入 */
export function draftToApi(d: DraftPrescription): PrescriptionDraftApi {
  return {
    source: d.source ?? (d.manual ? 'manual' : 'qr'),
    hospital: d.manual ? null : d.hospital || null,
    department: d.department || null,
    doctor: d.doctor || null,
    visit_date: d.visitDate,
    days: d.days ?? null,
    items: d.medicines.map((m) => ({
      name: m.name,
      license_no: m.licenseNo ?? null,
      purpose: m.effect || null,
      dose_qty: m.amount,
      quantity: m.quantity > 0 ? m.quantity : null,
      slots: m.slots,
      meal_timing: fromMeal(m.meal),
    })),
  }
}

/* ---------- 藥名搜尋 ---------- */

export function toDrugEntry(item: DrugSearchItem): DrugEntry {
  const doses = item.strengths.map((s) => s.label)
  return {
    name: item.name,
    zh: item.name_zh ?? undefined,
    doses: doses.length ? doses : ['不分劑量'],
    effect: '',
    common: item.common,
    source: item.common ? '北市聯醫常用藥' : '健保用藥品項',
    licenses: Object.fromEntries(item.strengths.map((s) => [s.label, s.license_no])),
  }
}

/* ---------- 緊急醫療卡 ---------- */

const GENDER_TO_ZH: Record<string, EmergencyCard['gender']> = { female: '女', male: '男' }
const BLOOD_TO_ZH: Record<string, EmergencyCard['bloodType']> = { A: 'A', B: 'B', O: 'O', AB: 'AB', unknown: '不知道' }

const allergyText = (c: CardOut, type: 'drug' | 'food') =>
  c.allergies.filter((a) => a.type === type).map((a) => a.name).join('、') || '無'

export function toCard(c: CardOut): EmergencyCard {
  return {
    name: c.name,
    birthday: isoToSlash(c.birth_date),
    gender: GENDER_TO_ZH[c.gender ?? ''] ?? '',
    bloodType: BLOOD_TO_ZH[c.blood_type] ?? '',
    contact1: c.contact ? { ...c.contact } : { name: '', relation: '', phone: '' },
    chronic: c.chronic_conditions,
    drugAllergy: c.has_consent ? allergyText(c, 'drug') : '',
    foodAllergy: c.has_consent ? allergyText(c, 'food') : '',
    special: c.special,
    language: (c.language ?? '') as EmergencyCard['language'],
    consent: c.has_consent,
    updatedAt: isoToSlash(c.updated_at),
  }
}

/** 「盤尼西林、海鮮」→ 清單；「無」或空白為空清單 */
const splitList = (text: string) =>
  text
    .split(/[、,，\s]+/)
    .map((s) => s.trim())
    .filter((s) => s && s !== '無')

export function cardToApi(card: EmergencyCard) {
  return {
    name: card.name.trim(),
    birth_date: card.birthday.trim().replace(/\//g, '-').replace(/-(\d)(?!\d)/g, '-0$1'),
    gender: card.gender === '女' ? 'female' : card.gender === '男' ? 'male' : null,
    blood_type: card.bloodType === '' || card.bloodType === '不知道' ? 'unknown' : card.bloodType,
    chronic_conditions: card.chronic,
    allergies: [
      ...splitList(card.drugAllergy).map((name) => ({ type: 'drug', name })),
      ...splitList(card.foodAllergy).map((name) => ({ type: 'food', name })),
    ],
    special: card.special,
    language: card.language || null,
    contact: { ...card.contact1 },
  }
}

export function toViewLogs(c: CardOut): ViewLog[] {
  return c.access_logs.map((log) => ({
    time: log.accessed_at,
    viewer: `救護人員（臺北市消防局 ${log.responder_unit}）`,
  }))
}

export function toRescueNotices(c: CardOut): RescueNotice[] {
  return c.access_logs.map((log) => ({
    time: log.accessed_at,
    unit: `臺北市政府消防局 ${log.responder_unit}`,
    staffId: log.responder_staff_no ?? '',
  }))
}

/** 救護人員查詢結果 → 醫療卡（救護人員看不到出生日期，只有年齡） */
export function responderCardToCard(r: ResponderCardOut): EmergencyCard {
  return {
    name: r.name,
    birthday: '',
    age: r.age,
    gender: GENDER_TO_ZH[r.gender ?? ''] ?? '',
    bloodType: BLOOD_TO_ZH[r.blood_type] ?? '',
    contact1: r.contact ? { name: r.contact.name, relation: r.contact.relation, phone: r.contact.phone } : { name: '', relation: '', phone: '' },
    chronic: r.chronic_conditions,
    drugAllergy: r.allergies.filter((a) => a.type === 'drug').map((a) => a.name).join('、'),
    foodAllergy: r.allergies.filter((a) => a.type === 'food').map((a) => a.name).join('、'),
    special: r.special,
    language: (r.language ?? '') as EmergencyCard['language'],
    consent: true,
    updatedAt: '',
  }
}

/** 醫療卡上的目前用藥（後端算好的，救護人員、家屬看到的和長者一致） */
export function doseToMedicine(d: DoseItemApi): Medicine {
  return { code: d.code, name: d.name, amount: d.qty, effect: d.purpose ?? '', slots: [], meal: '飯後', quantity: 0 }
}

/* ---------- 回診預約 ---------- */

export function toAppointment(a: AppointmentOut): Appointment {
  return {
    id: a.id,
    hospital: shortHospital(a.hospital.name),
    department: a.department,
    doctor: a.doctor,
    date: a.date,
    time: a.time.slice(0, 5),
    timeLabel: a.time_label,
    number: a.visit_no,
  }
}
