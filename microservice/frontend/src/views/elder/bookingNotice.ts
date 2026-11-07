import { HOSPITALS } from '@/data/mock'
import { activePrescriptions } from '@/store'
import type { Prescription } from '@/types'

/** 用來自動帶入院區／科別的藥單：第一張院區屬於聯合醫院的吃藥中藥單 */
export function prefillPrescription(now = new Date()): Prescription | undefined {
  return activePrescriptions(now).find((rx) => HOSPITALS.includes(rx.hospital))
}

export function bookingNotice(): string {
  const rx = prefillPrescription()
  const base = '目前提供臺北市立聯合醫院各院區。'
  return rx ? `${base}已從藥單 ${rx.code} 帶入科別。` : base
}
