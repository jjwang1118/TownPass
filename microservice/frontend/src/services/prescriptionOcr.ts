/**
 * 網址型藥袋二維碼：請後端下載網址中的藥單圖片並做文字辨識（OCR），整理成藥單資料
 * API 規格見 microservice/docs/qrcode_format.md「六、網址型二維碼：藥單辨識 API」
 *
 * 前端無法直接處理的原因：瀏覽器不能讀取其他網站圖片的內容（跨網域限制），OCR 也需在伺服器執行。
 */

/** 後端 API 位址，設定在 .env：VITE_API_BASE_URL=https://example.com */
const API_BASE = (import.meta.env.VITE_API_BASE_URL as string | undefined)?.replace(/\/$/, '') ?? ''

/** 等待辨識結果的上限 */
const TIMEOUT_MS = 30_000

/** 後端錯誤代碼 → 顯示給使用者的錯誤原因 */
const ERROR_REASONS: Record<string, string> = {
  INVALID_URL: '二維碼裡的網址格式不正確',
  URL_NOT_FOUND: '網址打不開（找不到這個網頁或圖片）',
  URL_FORBIDDEN: '網址打不開（網站拒絕存取）',
  DOWNLOAD_FAILED: '網址打不開（圖片下載失敗）',
  NOT_IMAGE: '網址的內容不是藥單圖片',
  IMAGE_TOO_LARGE: '藥單圖片太大，無法讀取',
  OCR_FAILED: '藥單圖片上的字讀不出來',
  NOT_PRESCRIPTION: '圖片上找不到藥單資料（藥名、用法、數量）',
  TIMEOUT: '讀取藥單逾時',
}

export class PrescriptionOcrError extends Error {
  constructor(
    public readonly code: string,
    reason: string,
  ) {
    super(reason)
  }
}

/** 二維碼內容是否為網址 */
export function isUrl(raw: string): boolean {
  return /^https?:\/\/\S+$/i.test(raw.trim())
}

/**
 * 送出網址給後端辨識，成功時回傳藥單 JSON 文字（格式同 qrcode_format.md，交給 parsePrescriptionQr 解析）
 * 失敗時丟出 PrescriptionOcrError，message 即為要顯示的錯誤原因
 */
export async function recognizePrescriptionFromUrl(imageUrl: string): Promise<string> {
  if (!isUrl(imageUrl)) throw new PrescriptionOcrError('INVALID_URL', ERROR_REASONS.INVALID_URL)
  if (!API_BASE) {
    throw new PrescriptionOcrError('SERVICE_UNAVAILABLE', '無法連線到藥單辨識服務（後端尚未設定）')
  }

  const controller = new AbortController()
  const timer = window.setTimeout(() => controller.abort(), TIMEOUT_MS)
  let res: Response
  try {
    res = await fetch(`${API_BASE}/api/prescriptions/ocr`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ imageUrl: imageUrl.trim() }),
      signal: controller.signal,
    })
  } catch (e) {
    if ((e as Error).name === 'AbortError') throw new PrescriptionOcrError('TIMEOUT', ERROR_REASONS.TIMEOUT)
    throw new PrescriptionOcrError('SERVICE_UNAVAILABLE', '無法連線到藥單辨識服務，請確認網路後再試一次')
  } finally {
    window.clearTimeout(timer)
  }

  let body: { prescription?: unknown; error?: { code?: string; message?: string } } = {}
  try {
    body = await res.json()
  } catch {
    /* 回應不是 JSON，下面以狀態碼判斷 */
  }

  if (!res.ok || !body.prescription) {
    const code = body.error?.code ?? `HTTP_${res.status}`
    const reason = ERROR_REASONS[code] ?? body.error?.message ?? `藥單辨識服務發生錯誤（${res.status}）`
    throw new PrescriptionOcrError(code, reason)
  }
  return JSON.stringify(body.prescription)
}
