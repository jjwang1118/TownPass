import { onBeforeUnmount, onMounted } from 'vue'
import { SLOTS } from '@/data/constants'
import { activeMedicines, appointmentTime, state, upcomingAppointments } from '@/store'
import { amountText, medicinesInSlot } from '@/utils/schedule'
import { toISODate } from '@/utils/date'
import { notify } from './flutterBridge'

/** 時段到後幾分鐘內仍會補發提醒 */
const WINDOW_MINUTES = 5

/** CM-ALT-02 用藥提醒內文：B1、B2 各 1 顆，點開可以聽語音 */
export function medicineReminderBody(codesAmounts: { code: string; amount: number }[]): string {
  const amounts = new Set(codesAmounts.map((c) => c.amount))
  let text: string
  if (codesAmounts.length > 1 && amounts.size === 1) {
    text = `${codesAmounts.map((c) => c.code).join('、')} 各 ${amountText(codesAmounts[0].amount)}`
  } else {
    text = codesAmounts.map((c) => `${c.code} ${amountText(c.amount)}`).join('、')
  }
  return `${text}，點開可以聽語音`
}

/** 只有長者端畫面發送提醒（家屬的推播需由後端發送） */
function isElderView(): boolean {
  const hash = window.location.hash
  return hash === '' || hash === '#/' || hash.startsWith('#/elder')
}

function check() {
  if (!isElderView()) return
  const now = new Date()
  const today = toISODate(now)
  const minutes = now.getHours() * 60 + now.getMinutes()
  const meds = activeMedicines(now)

  // 用藥提醒：9:00、12:00、18:00、22:00
  SLOTS.forEach((slot) => {
    const key = `slot:${today}:${slot.key}`
    if (state.notified.includes(key)) return
    if (minutes < slot.minutes || minutes >= slot.minutes + WINDOW_MINUTES) return
    const list = medicinesInSlot(meds, slot.key)
    if (list.length === 0) return
    notify(`${slot.name} ${slot.time} 該吃藥了`, medicineReminderBody(list))
    state.notified.push(key)
  })

  // 回診提醒：每一筆預約各自在回診前 1 小時提醒（與用藥提醒互相獨立）
  upcomingAppointments(now).forEach((appt) => {
    const diffMin = (appointmentTime(appt).getTime() - now.getTime()) / 60000
    const key = `appt:${appt.date}:${appt.time}:${appt.doctor}`
    if (diffMin <= 60 && diffMin > 60 - WINDOW_MINUTES && !state.notified.includes(key)) {
      notify(`今天 ${appt.time} 要回診`, `${appt.hospital}${appt.department}${appt.doctor}，記得帶健保卡`)
      state.notified.push(key)
    }
  })

  // 只保留今天的紀錄
  state.notified = state.notified.filter((k) => !k.startsWith('slot:') || k.startsWith(`slot:${today}`))
}

/** 長者端：App 開啟期間依時段發送用藥／回診提醒 */
export function useReminders() {
  let timer = 0
  onMounted(() => {
    check()
    timer = window.setInterval(check, 30_000)
  })
  onBeforeUnmount(() => window.clearInterval(timer))
}
