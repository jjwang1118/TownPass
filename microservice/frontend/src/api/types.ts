/** 後端 API 的回應格式（只列前端用到的欄位，完整定義見 http://localhost:8000/docs） */
import type { SlotKey } from '@/types'

export type MealTimingApi = 'before' | 'after'

/** 裝置端 OCR 整理的原始欄位；讀不到的值留空，由後端比對並標示待核對。 */
export interface PhotoItemIn {
  name: string | null
  license_no?: string | null
  strength?: string | null
  purpose?: string | null
  dose_qty: number | null
  quantity: number | null
  frequency: 'QD' | 'BID' | 'TID' | 'QID' | 'HS' | null
  meal_timing: MealTimingApi | null
  confidence: Record<string, number>
}

export interface PhotoRecognitionIn {
  hospital: string | null
  department: string | null
  doctor: string | null
  visit_date: string | null
  days: number | null
  items: PhotoItemIn[]
  confidence: Record<string, number>
}

export interface MeOut {
  id: string
  role: 'elder' | 'family' | null
  real_name: string
}

export interface TokenOut {
  access_token: string
  user: MeOut
}

export interface MedicationOut {
  id: string
  code: string
  seq: number
  name: string
  license_no: string | null
  purpose: string | null
  dose_qty: number
  quantity: number | null
  slots: { slot_key: SlotKey }[]
  meal_timing: MealTimingApi
  days_left: number
  status: 'active' | 'stopped'
}

export interface PrescriptionOut {
  id: string
  letter: string
  source: 'photo' | 'qr' | 'manual'
  hospital: string | null
  department: string | null
  doctor: string | null
  visit_date: string
  days: number | null
  days_left: number
  status: 'active' | 'finished'
  medications: MedicationOut[]
}

export interface DraftItemApi {
  name: string
  license_no?: string | null
  strength?: string | null
  purpose?: string | null
  dose_qty: number
  quantity?: number | null
  slots: SlotKey[]
  meal_timing: MealTimingApi
  needs_review?: boolean
}

export interface PrescriptionDraftApi {
  source: 'photo' | 'qr' | 'manual'
  hospital?: string | null
  department?: string | null
  doctor?: string | null
  visit_date: string
  days?: number | null
  items: DraftItemApi[]
}

export interface MedicationWarningApi {
  type: 'same_ingredient'
  code: string
  with_code: string
  message: string
}

export interface PreviewOut {
  letter: string
  draft: PrescriptionDraftApi
  items: { code: string; uncertain: boolean; uncertain_fields: string[] }[]
  uncertain: { field: string; confidence: number; message: string }[]
  warnings: MedicationWarningApi[]
}

export interface PrescriptionCreated {
  prescription: PrescriptionOut
  warnings: MedicationWarningApi[]
  message: string
}

export interface DrugSearchItem {
  name: string
  name_zh: string | null
  ingredient: string | null
  form: string | null
  strengths: { label: string; license_no: string }[]
  common: boolean
}

export interface ContactApi {
  name: string
  relation: string
  phone: string
}

export interface CardOut {
  name: string
  birth_date: string | null
  gender: 'male' | 'female' | 'other' | null
  blood_type: 'A' | 'B' | 'O' | 'AB' | 'unknown'
  contact: ContactApi | null
  chronic_conditions: string[]
  allergies: { type: 'drug' | 'food'; name: string }[]
  special: string[]
  language: string | null
  current_medications: DoseItemApi[]
  code: { code: string; qr_url: string } | null
  has_consent: boolean
  access_logs: {
    responder_name: string
    responder_unit: string
    responder_staff_no: string | null
    accessed_at: string
  }[]
  updated_at: string
}

export interface DoseItemApi {
  code: string
  name: string
  qty: number
  purpose: string | null
  meal_timing_label: string
}

export interface ResponderCardOut {
  name: string
  age: number | null
  gender: CardOut['gender']
  blood_type: CardOut['blood_type']
  contact: (ContactApi & { call: { name: string; data: string } }) | null
  chronic_conditions: string[]
  allergies: CardOut['allergies']
  special: string[]
  language: string | null
  current_medications: DoseItemApi[]
  disclaimer: string
  close_at: string
}

export interface ResponderTokenOut {
  access_token: string
  name: string
  unit: string
  staff_no: string
}

export interface InviteOut {
  code: string
  expires_at: string
}

export interface BindingOut {
  id: string
  elder_id: string
  elder_name: string
  elder_phone: string
  family_id: string
  family_name: string
  relation_label: string
}

export interface HospitalOut {
  id: string
  name: string
  address: string
}

export interface DepartmentOut {
  id: string
  name: string
  last_visited: boolean
  from_letter: string | null
}

export interface DoctorOut {
  id: string
  name: string
  last_visited: boolean
  schedule: string
  available: boolean
  note: string | null
}

export interface ClinicDayOut {
  session_id: string
  date: string
  label: string
  period_label: string
  available: boolean
  note: string | null
}

export interface SlotOut {
  slot_id: string
  time: string
  label: string
  remaining: number
  available: boolean
  note: string
}

export interface AppointmentOut {
  id: string
  hospital: HospitalOut
  department: string
  doctor: string
  date: string
  date_label: string
  time: string
  time_label: string
  visit_no: number
  status: 'booked' | 'cancelled'
}
