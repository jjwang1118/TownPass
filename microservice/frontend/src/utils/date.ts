const WEEKDAY_ZH = ['日', '一', '二', '三', '四', '五', '六']

const pad = (n: number) => String(n).padStart(2, '0')

/** 'YYYY-MM-DD' → 當地時間 Date（00:00） */
export function parseDate(iso: string): Date {
  const [y, m, d] = iso.split('-').map(Number)
  return new Date(y, m - 1, d)
}

export function toISODate(date: Date): string {
  return `${date.getFullYear()}-${pad(date.getMonth() + 1)}-${pad(date.getDate())}`
}

export function addDays(date: Date, days: number): Date {
  const d = new Date(date)
  d.setDate(d.getDate() + days)
  return d
}

/** 兩個日期相差的天數（忽略時分） */
export function diffDays(from: Date, to: Date): number {
  const a = new Date(from.getFullYear(), from.getMonth(), from.getDate()).getTime()
  const b = new Date(to.getFullYear(), to.getMonth(), to.getDate()).getTime()
  return Math.round((b - a) / 86400000)
}

/** 11/14（五） */
export function formatMonthDayWeek(iso: string): string {
  const d = parseDate(iso)
  return `${d.getMonth() + 1}/${pad(d.getDate())}（${WEEKDAY_ZH[d.getDay()]}）`
}

/** 11/05 */
export function formatMonthDay(iso: string): string {
  const d = parseDate(iso)
  return `${pad(d.getMonth() + 1)}/${pad(d.getDate())}`
}

/** 2026/11/05 */
export function formatSlashDate(iso: string): string {
  return iso.replace(/-/g, '/')
}

/** 11 月 7 日（六） */
export function formatLongDate(date: Date): string {
  return `${date.getMonth() + 1} 月 ${date.getDate()} 日（${WEEKDAY_ZH[date.getDay()]}）`
}

/** HH:mm */
export function formatClock(date: Date): string {
  return `${pad(date.getHours())}:${pad(date.getMinutes())}`
}

/** ISO datetime → 11/07 14:32 */
export function formatDateTime(isoDateTime: string): string {
  const d = new Date(isoDateTime)
  return `${pad(d.getMonth() + 1)}/${pad(d.getDate())} ${formatClock(d)}`
}

/** 時段問候 */
export function greeting(date: Date): string {
  const h = date.getHours()
  if (h >= 5 && h < 11) return '早安'
  if (h >= 11 && h < 18) return '午安'
  return '晚安'
}

/** 足歲年齡，birthday 為 YYYY/MM/DD */
export function ageOf(birthday: string, now: Date): number | null {
  const m = birthday.match(/^(\d{4})[/-](\d{1,2})[/-](\d{1,2})$/)
  if (!m) return null
  const [y, mo, d] = [Number(m[1]), Number(m[2]), Number(m[3])]
  let age = now.getFullYear() - y
  if (now.getMonth() + 1 < mo || (now.getMonth() + 1 === mo && now.getDate() < d)) age -= 1
  return age
}

/** 秒數 → MM:SS */
export function formatCountdown(totalSeconds: number): string {
  const s = Math.max(0, Math.floor(totalSeconds))
  return `${pad(Math.floor(s / 60))}:${pad(s % 60)}`
}
