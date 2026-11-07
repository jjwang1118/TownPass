/**
 * 與城市通 App（Flutter WebView）溝通。
 * 透過 window.flutterObject 收發 { name, data }，雙向都是 JSON 字串。
 * 一般瀏覽器沒有 flutterObject，改用瀏覽器能力或模擬資料。
 * 內建 name：userinfo、launch_map、phone_call、location、deviceinfo、open_link、notify、qr_code_scan
 */

interface AppMessage<T = unknown> {
  name: string
  data: T
}

export function isInApp(): boolean {
  return typeof window !== 'undefined' && typeof window.flutterObject !== 'undefined'
}

export function postToApp(name: string, data?: unknown): void {
  window.flutterObject?.postMessage(JSON.stringify({ name, data }))
}

/** 送出訊息並等待同名回覆；用完即移除 listener，避免重複觸發 */
export function requestFromApp<T>(name: string, data?: unknown, timeoutMs = 120_000): Promise<T | null> {
  const fo = window.flutterObject
  if (!fo) return Promise.resolve(null)
  return new Promise((resolve) => {
    let timer = 0
    const listener = (event: MessageEvent) => {
      let msg: AppMessage<T>
      try {
        msg = (typeof event.data === 'string' ? JSON.parse(event.data) : event.data) as AppMessage<T>
      } catch {
        return
      }
      if (msg?.name !== name) return
      window.clearTimeout(timer)
      fo.removeEventListener('message', listener)
      resolve(msg.data ?? null)
    }
    fo.addEventListener('message', listener)
    timer = window.setTimeout(() => {
      fo.removeEventListener('message', listener)
      resolve(null)
    }, timeoutMs)
    postToApp(name, data)
  })
}

/** 撥電話：App 內用 phone_call，瀏覽器用 tel: 連結 */
export function phoneCall(phone: string): void {
  const digits = phone.replace(/[^\d+]/g, '')
  if (!digits) return
  if (isInApp()) {
    postToApp('phone_call', digits)
    return
  }
  window.location.href = `tel:${digits}`
}

/** 手機通知：App 內用 notify，瀏覽器用 Notification API（需使用者允許） */
export function notify(title: string, content: string): void {
  if (isInApp()) {
    postToApp('notify', { title, content })
    return
  }
  if (!('Notification' in window)) return
  try {
    if (Notification.permission === 'granted') {
      new Notification(title, { body: content })
    }
  } catch {
    /* 部分瀏覽器（如 Android Chrome）不支援直接建立 Notification */
  }
}

/** 開啟 App 內建 QR Code 掃描，回傳掃描內容；瀏覽器回傳 null */
export async function scanQrCode(): Promise<string | null> {
  if (!isInApp()) return null
  const result = await requestFromApp<unknown>('qr_code_scan')
  if (result == null) return null
  return typeof result === 'string' ? result : JSON.stringify(result)
}

interface TownPassAccount {
  realName?: string
  [key: string]: unknown
}

/** 台北通帳號資訊；瀏覽器回傳 null */
export async function getUserInfo(): Promise<TownPassAccount | null> {
  if (!isInApp()) return null
  const data = await requestFromApp<TownPassAccount | []>('userinfo', undefined, 10_000)
  if (!data || Array.isArray(data)) return null
  return data
}
