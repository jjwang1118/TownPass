/**
 * 拍藥袋：在手機上（WebView 或瀏覽器裡）用 Tesseract 辨識藥袋照片上的字，回傳由上到下的每一行。
 *
 * - 推論在裝置端：tesseract.js（Apache-2.0）以 WebAssembly 執行；worker、核心與繁中／英文字庫
 *   放在 public/tesseract/，和前端一起部署，不向 CDN 下載，關閉網路也能用（規格書 §8.3）。
 * - 辨識出的文字送後端 /prescriptions/ocr-preview，由後端用規則整理成藥單欄位。
 * - 引擎第一次載入需要幾秒；離開拍藥袋頁時呼叫 releaseBagOcr() 釋放記憶體（WebView 注意事項）。
 */
import { createWorker, OEM, PSM, type Worker } from 'tesseract.js'

/**
 * public/tesseract/ 的完整網址。vite.config 的 base 是 './'（可部署在任意子路徑），而 tesseract.js 的 worker
 * 可能以 blob: 網址執行，相對路徑不可靠；所以建置後用本程式所在的 assets/ 往上一層算出完整網址，開發時在網站根目錄。
 */
const BASE = import.meta.env.DEV ? '/tesseract' : new URL('../tesseract', import.meta.url).href
/** 照片長邊縮到這個像素：夠讀藥袋上的字，又不會太慢 */
const MAX_SIDE = 2000
/** 和後端 OcrScanData 相同的上限 */
const MAX_LINES = 200
const MAX_LINE_LENGTH = 200

let workerPromise: Promise<Worker> | null = null
let onProgress: ((ratio: number) => void) | null = null

function getWorker(): Promise<Worker> {
  workerPromise ??= createWorker(['chi_tra', 'eng'], OEM.LSTM_ONLY, {
    workerPath: `${BASE}/worker.min.js`,
    corePath: `${BASE}/core`,
    langPath: `${BASE}/lang`,
    gzip: true,
    logger: (m) => {
      if (m.status === 'recognizing text') onProgress?.(m.progress)
    },
  })
    .then(async (worker) => {
      // SINGLE_BLOCK：藥袋是由上到下一行一行的字，實測比自動版面分析準很多（AUTO 常漏掉每行第一個字、打亂順序）
      // preserve_interword_spaces：保留大空白，後端靠它分開「心臟內科　王醫師」這類並排的欄位
      await worker.setParameters({ tessedit_pageseg_mode: PSM.SINGLE_BLOCK, preserve_interword_spaces: '1' })
      return worker
    })
    .catch((e: unknown) => {
      workerPromise = null // 下次重新載入
      throw e
    })
  return workerPromise
}

/** 先在背景載入引擎與字庫，讓長輩按下拍照後不用等太久 */
export function warmUpBagOcr(): void {
  getWorker().catch(() => undefined)
}

/** 離開拍藥袋頁時釋放 OCR 引擎 */
export async function releaseBagOcr(): Promise<void> {
  const pending = workerPromise
  workerPromise = null
  if (pending) await (await pending.catch(() => null))?.terminate()
}

/** 照片縮小並轉成 canvas（大照片在手機上辨識很慢，也容易記憶體不足） */
async function toCanvas(file: Blob): Promise<HTMLCanvasElement> {
  const bitmap = await createImageBitmap(file)
  const scale = Math.min(1, MAX_SIDE / Math.max(bitmap.width, bitmap.height))
  const canvas = document.createElement('canvas')
  canvas.width = Math.round(bitmap.width * scale)
  canvas.height = Math.round(bitmap.height * scale)
  canvas.getContext('2d')?.drawImage(bitmap, 0, 0, canvas.width, canvas.height)
  bitmap.close()
  return canvas
}

/**
 * 辨識藥袋照片，回傳每一行文字（去掉空行）。
 * progress：辨識進度 0～1，給畫面顯示「正在辨識…」。
 */
export async function recognizeBagLines(file: Blob, progress?: (ratio: number) => void): Promise<string[]> {
  const [worker, canvas] = await Promise.all([getWorker(), toCanvas(file)])
  onProgress = progress ?? null
  try {
    const { data } = await worker.recognize(canvas)
    return data.text
      .split('\n')
      .map((line) => line.replace(/[ \t]+$/, '').trimStart())
      .filter((line) => line.trim() !== '')
      .slice(0, MAX_LINES)
      .map((line) => line.slice(0, MAX_LINE_LENGTH))
  } finally {
    onProgress = null
  }
}
