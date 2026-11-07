import { state } from '@/store'

/** 「目前提供臺北市立聯合醫院各院區。已從藥單 A 帶入科別。」 */
export function bookingNotice(): string {
  const base = '目前提供臺北市立聯合醫院各院區。'
  const letter = state.booking.fromLetter
  return letter && state.booking.department ? `${base}已從藥單 ${letter} 帶入科別。` : base
}
