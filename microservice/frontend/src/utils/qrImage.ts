/**
 * 從使用者上傳的照片辨識 QR Code
 * - 優先使用瀏覽器內建 BarcodeDetector（Android Chrome／WebView 支援）
 * - 不支援時改用 jsQR（Apache-2.0）從圖片像素辨識
 */
import jsQR from 'jsqr'

/** 辨識用的最大邊長：照片太大會很慢，先縮小 */
const MAX_SIZE = 1280

async function loadImage(file: File): Promise<HTMLImageElement> {
  const url = URL.createObjectURL(file)
  try {
    const img = new Image()
    img.src = url
    await img.decode()
    return img
  } finally {
    // decode 完成後圖片已載入，可釋放網址
    setTimeout(() => URL.revokeObjectURL(url), 0)
  }
}

async function detectWithBarcodeDetector(img: HTMLImageElement): Promise<string | null> {
  const Detector = window.BarcodeDetector
  if (!Detector) return null
  try {
    const codes = await new Detector({ formats: ['qr_code'] }).detect(img)
    return codes[0]?.rawValue ?? null
  } catch {
    return null
  }
}

function detectWithJsQr(img: HTMLImageElement): string | null {
  const scale = Math.min(1, MAX_SIZE / Math.max(img.naturalWidth, img.naturalHeight))
  const width = Math.max(1, Math.round(img.naturalWidth * scale))
  const height = Math.max(1, Math.round(img.naturalHeight * scale))
  const canvas = document.createElement('canvas')
  canvas.width = width
  canvas.height = height
  const ctx = canvas.getContext('2d', { willReadFrequently: true })
  if (!ctx) return null
  ctx.drawImage(img, 0, 0, width, height)
  const { data } = ctx.getImageData(0, 0, width, height)
  return jsQR(data, width, height, { inversionAttempts: 'attemptBoth' })?.data ?? null
}

/** 回傳 QR Code 內容；圖片中找不到 QR Code 時回傳 null */
export async function decodeQrFromFile(file: File): Promise<string | null> {
  const img = await loadImage(file)
  return (await detectWithBarcodeDetector(img)) ?? detectWithJsQr(img)
}
