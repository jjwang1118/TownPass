import type { PhotoItemIn, PhotoRecognitionIn } from '@/api/types'

/** OCR \u6a21\u578b\uff08PP-OCRv5 \u7e41\u7c21\u5171\u7528\uff09\u5e38\u628a\u85e5\u888b\u95dc\u9375\u5b57\u8fa8\u8b58\u6210\u7c21\u9ad4\u5b57\uff0c\u5148\u8f49\u56de\u7e41\u9ad4\uff0c\u6b04\u4f4d\u898f\u5247\u624d\u6bd4\u5c0d\u5f97\u5230\u3002 */
const TRADITIONAL: Record<string, string> = {
  \u8bca: '\u8a3a', \u522b: '\u5225', \u533b: '\u91ab', \u5185: '\u5167', \u836f: '\u85e5', \u8d39: '\u8cbb', \u5355: '\u55ae', \u6570: '\u6578', \u9897: '\u9846', \u5242: '\u5291',
  \u9002: '\u9069', \u5e94: '\u61c9', \u5904: '\u8655', \u8c03: '\u8abf', \u5e08: '\u5e2b', \u79f0: '\u7a31', \u996d: '\u98ef', \u540e: '\u5f8c', \u65f6: '\u6642', \u603b: '\u7e3d',
  \u7ed9: '\u7d66', \u4e24: '\u5169', \u53f7: '\u865f', \u533a: '\u5340', \u8bdd: '\u8a71', \u8bc1: '\u8b49', \u7ec6: '\u7d30', \u95e8: '\u9580', \u7597: '\u7642', \u4e2a: '\u500b',
}

function normalize(text: string): string {
  return text
    .normalize('NFKC')
    .replace(/\r/g, '')
    .replace(/[\u8bca\u522b\u533b\u5185\u836f\u8d39\u5355\u6570\u9897\u5242\u9002\u5e94\u5904\u8c03\u5e08\u79f0\u996d\u540e\u65f6\u603b\u7ed9\u4e24\u53f7\u533a\u8bdd\u8bc1\u7ec6\u95e8\u7597\u4e2a]/g, (char) => TRADITIONAL[char])
    .replace(/([\u3400-\u9fff])[\t ]+(?=[\u3400-\u9fff])/g, '$1')
    // \u300c9.0TB\u300d\u7684 0 \u5076\u723e\u88ab\u8fa8\u8b58\u6210\u5b57\u6bcd D\uff0fO
    .replace(/(\d)\.[DO](?=\s*(?:TB|TE|TAB|CAP)\b)/gi, '$1.0')
}

/** OCR \u6703\u628a\u82f1\u6587\u85e5\u540d\u5f9e\u4e2d\u9593\u65b7\u958b\uff08DI -me thy lephedrine\uff09\uff0c\u628a\u88ab\u5207\u51fa\u7684\u77ed\u5c0f\u5beb\u7247\u6bb5\u63a5\u56de\u53bb\u3002 */
function tidyName(name: string): string {
  const tokens = name.replace(/\s*-\s*/g, '-').split(/\s+/).filter(Boolean)
  const joined: string[] = []
  tokens.forEach((token, index) => {
    const tail = tokens[index - 1]?.match(/[a-z]+$/)?.[0]
    const head = token.match(/^[a-z]+/)?.[0]
    if (joined.length && tail && head && (tail.length <= 3 || head.length <= 3)) joined[joined.length - 1] += token
    else joined.push(token)
  })
  return joined.join(' ')
}

/** OCR \u6587\u5b57\u6846\uff1abox \u4f9d\u5e8f\u70ba\u5de6\u4e0a\u3001\u53f3\u4e0a\u3001\u53f3\u4e0b\u3001\u5de6\u4e0b\u7684 [x, y]\u3002 */
export interface OcrBox {
  text: string
  mean: number
  box: [number, number][]
}

/**
 * \u4f9d\u6587\u5b57\u6846\u4f4d\u7f6e\u628a\u540c\u4e00\u5217\u7684\u6587\u5b57\u63a5\u6210\u4e00\u884c\uff08\u7531\u5de6\u81f3\u53f3\uff09\uff0c\u5404\u5217\u7531\u4e0a\u81f3\u4e0b\u6392\u5217\uff1b
 * \u85e5\u888b\u8868\u683c\u540c\u4e00\u5217\u7684\u85e5\u540d\u8207\u7528\u6cd5\u5e38\u88ab\u62c6\u6210\u4e0d\u540c\u6587\u5b57\u6846\uff0c\u63a5\u56de\u540c\u4e00\u884c\u6b04\u4f4d\u898f\u5247\u624d\u80fd\u4e00\u8d77\u89e3\u6790\u3002
 * confidence \u70ba 0\uff5e100 \u7684\u5e73\u5747\u8fa8\u8b58\u5206\u6578\u3002
 */
export function joinOcrRows(boxes: OcrBox[]): { text: string; confidence: number } {
  const items = boxes
    .filter((item) => item.text.trim() && item.box?.length)
    .map((item) => {
      const xs = item.box.map((point) => point[0])
      const ys = item.box.map((point) => point[1])
      return { text: item.text.trim(), mean: item.mean, left: Math.min(...xs), top: Math.min(...ys), bottom: Math.max(...ys) }
    })
    .sort((a, b) => a.top + a.bottom - (b.top + b.bottom))
  const rows: (typeof items)[] = []
  for (const item of items) {
    const row = rows[rows.length - 1]
    const center = (item.top + item.bottom) / 2
    if (row && row.some((other) => center > other.top && center < other.bottom)) row.push(item)
    else rows.push([item])
  }
  const text = rows.map((row) => row.sort((a, b) => a.left - b.left).map((item) => item.text).join(' ')).join('\n')
  const scores = items.map((item) => item.mean).filter(Number.isFinite)
  const confidence = scores.length ? (scores.reduce((sum, value) => sum + value, 0) / scores.length) * 100 : 0
  return { text, confidence }
}

function positive(value: string | undefined, max: number): number | null {
  if (!value) return null
  const number = Number(value)
  return Number.isFinite(number) && number > 0 && number <= max && Number.isInteger(number * 10) ? number : null
}

function numeric(value: string): string {
  return ({ 半: '0.5', 一: '1', 二: '2', 兩: '2', 三: '3', 四: '4' } as Record<string, string>)[value] ?? value
}

function visitDate(text: string): string | null {
  const match = text.match(/(?:就診|看診|處方|調劑)日(?:期)?\s*[:;：]?\s*(\d{2,4})[./-](\d{1,2})[./-](\d{1,2})/)
  if (!match) return null
  const year = Number(match[1]) + (match[1].length <= 3 ? 1911 : 0)
  const month = Number(match[2])
  const day = Number(match[3])
  const date = new Date(Date.UTC(year, month - 1, day))
  if (year < 1900 || year > 2100 || date.getUTCFullYear() !== year || date.getUTCMonth() !== month - 1 || date.getUTCDate() !== day) return null
  return `${year}-${String(month).padStart(2, '0')}-${String(day).padStart(2, '0')}`
}

function frequency(text: string): PhotoItemIn['frequency'] {
  const code = text.match(/\b(QID|TID|BID|QD|HS)\b/i)?.[1].toUpperCase()
  if (code) return code as NonNullable<PhotoItemIn['frequency']>
  const times = text.match(/(?:每日|每天|一天)\s*([一二兩三四1-4])\s*次/)
  if (times) return ({ 1: 'QD', 2: 'BID', 3: 'TID', 4: 'QID' } as const)[Number(numeric(times[1])) as 1 | 2 | 3 | 4]
  const hours = text.match(/\bQ(6|8|12|24)H\b/i)?.[1]
    ?? text.match(/每\s*(6|8|12|24|六|八|十二|二十四)\s*(?:個)?小時/)?.[1]
  if (hours) return ({ 6: 'QID', 六: 'QID', 8: 'TID', 八: 'TID', 12: 'BID', 十二: 'BID', 24: 'QD', 二十四: 'QD' } as Record<string, PhotoItemIn['frequency']>)[hours] ?? null
  if (/睡前/.test(text)) return 'HS'
  return null
}

interface MedicineLine {
  name: string
  dosing: string
}

function medicineLines(lines: string[]): MedicineLine[] {
  // 表格列先以明確的給藥途徑分隔藥名與數量；容許途徑內個別字的 OCR 錯字。
  const rows = lines.flatMap((line): MedicineLine[] => {
    const row = line.match(/^(.{2,128}?)\s*[\[【(（](?:內|口|外|眼|耳|鼻|注)[^\]】)）]{0,4}[\]】)）]\s*(.*)$/)
    return row ? [{ name: row[1].trim(), dosing: row[2].trim() }] : []
  })
  if (rows.length) return rows

  const labeled = lines.flatMap((line): MedicineLine[] => {
    const match = line.match(/^(?:藥品名稱|藥品名|藥名|品名)\s*[:：]\s*(.+)$/)
      ?? line.match(/^商品名\s*[:：]?\s*(.+)$/)
    if (!match) return []
    const [name, ...dosing] = match[1].split(/\s+(?=每次|一次|每日|每天|用法|用量)|(?=成分|成份|適應症)/)
    return name.trim() ? [{ name: name.trim(), dosing: dosing.join(' ') }] : []
  })
  if (labeled.length) return labeled

  // 編號表格列（醫院藥袋常見）：「1. TOPIRAMATE 100MG 2.00 粒 21 HS 42.0 睡前一次」
  // 英文藥名後第一個兩位小數為每次用量；OCR 常把藥名與用量黏在一起（100MO2.00）或漏讀開頭編號，皆可接受。
  return lines.flatMap((line): MedicineLine[] => {
    const row = line.match(/^(?:\d{1,2}\s*[.)、]\s*)?([A-Za-z][^\n]{2,80}?)\s*(\d{1,2}\.\d{2})(.*)$/)
    if (!row || (row[1].match(/[A-Za-z]/g)?.length ?? 0) < 4) return []
    // 欄位依序為：每次用量、天數（整數）、用法、簡碼、總量（一位小數，如 42.0）。
    // 標上「每次／天／總量」交給下方既有的欄位規則讀取。
    const rest = row[3].trim()
    const days = rest.match(/^(\d{1,3})(?![\d.])/)?.[1]
    const found = days ? rest.slice(days.length).match(/(?:^|[^\d.])(\d{1,4}\.\d)(?![\d.])/)?.[1] : undefined
    // 簡碼與總量常黏在一起（OTOP3 + 21.0 → 321.0）：超過「每次用量 × 天數 × 一天 4 次」就不採用
    const total = found && Number(found) <= Number(row[2]) * Number(days) * 4 ? found : undefined
    const labels = [`每次 ${row[2]}`, days && `${days}天`, total && `總量:${total}`].filter(Boolean).join(' ')
    return [{ name: row[1].trim(), dosing: `${labels} ${rest}`.trim() }]
  })
}

/**
 * 支援有「藥名／商品名」標籤、給藥途徑表格列，或編號表格列（英文藥名＋每次用量）的印刷藥袋。
 * 文字辨識分數不等於欄位正確率，規則解析一律保守標示待核對；不推測缺少的用法。
 */
export function parsePrescriptionText(rawText: string, textConfidence: number): PhotoRecognitionIn {
  const text = normalize(rawText)
  const lines = text.split('\n').map((line) => line.trim()).filter(Boolean)
  const medicines = medicineLines(lines)
  if (!medicines.length) throw new Error('照片中找不到可辨識的藥名，請換一張清楚的藥袋照片，或改用手動輸入。')
  if (medicines.length > 20) throw new Error('照片中的藥品太多，請分開拍攝或選擇照片。')

  const confidence = Number.isFinite(textConfidence) ? Math.min(0.75, Math.max(0, textConfidence / 100)) : 0
  const score = (value: unknown) => value === null || value === '' ? 0 : confidence
  const hospital = lines.map((line) => line.match(/([^\s:：()（）]{2,48}(?:醫院|診所|院區))/)?.[1]).find(Boolean) ?? null
  const department = text.match(/科別\s*[:：]\s*([^\s:：,，]{1,20})/)?.[1] ?? null
  // 醫師姓名後面常緊接「藥局地點」「調劑者」等其他欄位，遇到這些字就停
  const doctor = text.match(/(?:醫師|醫生)\s*[:：]\s*([^\s:：,，]{2,12}?)(?=藥局|藥師|調劑|地點|科別|[\s:：,，]|$)/)?.[1] ?? null
  const date = visitDate(text)
  const duration = text.match(/(?:給藥天數|用藥天數|服用天數|日數)\s*[:：]?\s*(\d{1,3})/)?.[1]
  // 各藥的天數：超過一半的藥相同時才當整張藥單的天數（OCR 偶爾把 21 讀成 71）；各藥天數不同時不合併
  const rowDurations = medicines.flatMap((item) => [...new Set([...item.dosing.matchAll(/(?:^|[^\d.])(\d{1,3})\s*天/g)].map((match) => match[1]))])
  const counts = new Map<string, number>()
  rowDurations.forEach((value) => counts.set(value, (counts.get(value) ?? 0) + 1))
  const commonDuration = [...counts].find(([, count]) => count * 2 > medicines.length)?.[0]
  const days = positive(duration ?? commonDuration, 365)
  const directions = lines.filter((line) => /^(?:用法|服法|用量|每次|一次|每日|每天|服用方法|服用時間|用藥方法)\s*[:：]?/.test(line)).join(' ')

  const items: PhotoItemIn[] = medicines.map((medicine) => {
    const dosing = medicines.length === 1 ? `${medicine.dosing} ${directions}` : medicine.dosing
    const dose = dosing.match(/(?:每次(?:用量)?|一次)\s*[:：]?\s*(半|[一二兩三四]|\d+(?:\.\d+)?)\s*(?:顆|錠|粒|包|毫升|ml)?/i)?.[1]
      ?? medicine.dosing.match(/^(\d+(?:\.\d+)?)\s+(?=\d)/)?.[1]
    const total = dosing.match(/(?:總量|總顆數|總數量)\s*[:：]\s*(\d+(?:\.\d+)?)/)?.[1]
      ?? medicine.dosing.match(/(?:^|\s)(\d+(?:\.\d+)?)\s*(?:(?:TB|TE|TAB|CAP)\b|顆|錠|粒|包)/i)?.[1]
      ?? (medicines.length === 1 ? text.match(/(?:總量|總顆數|總數量)\s*[:：]\s*(\d+(?:\.\d+)?)/)?.[1] : undefined)
    const before = /飯前|餐前|\bAC\b/i.test(dosing)
    const after = /飯後|餐後|\bPC\b/i.test(dosing)
    const strength = medicine.name.match(/\d+(?:\.\d+)?\s*(?:(?:mcg|mg|g)\b|毫克|微克|公克)/i)?.[0] ?? null
    const purpose = medicines.length === 1 ? text.match(/適應症\s*[:：]\s*([^\n]{1,128})/)?.[1] ?? null : null
    const item: PhotoItemIn = {
      name: tidyName(medicine.name.replace(/^\d+[.)、]\s*/, '')).slice(0, 128),
      strength,
      purpose,
      dose_qty: positive(dose ? numeric(dose) : undefined, 99.9),
      quantity: positive(total, 99999.9),
      frequency: frequency(dosing),
      meal_timing: before !== after ? before ? 'before' : 'after' : null,
      confidence: {},
    }
    item.confidence = Object.fromEntries(['name', 'strength', 'purpose', 'dose_qty', 'quantity', 'frequency', 'meal_timing'].map((field) => [field, score(item[field as keyof PhotoItemIn])]))
    return item
  })

  return {
    hospital, department, doctor, visit_date: date, days, items,
    confidence: { hospital: score(hospital), department: score(department), doctor: score(doctor), visit_date: score(date), days: score(days) },
  }
}
