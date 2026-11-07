/**
 * 裝置端藥袋 OCR：PaddleOCR PP-OCRv5 手機版模型（Apache-2.0）＋ esearch-ocr（Apache-2.0）＋ onnxruntime-web（MIT）。
 * App 內與瀏覽器都使用同一套；實測 PaddleOCR 比 Google ML Kit 準確，且 ML Kit 非開源授權，已不採用。
 * 模型與 wasm 隨網頁一起部署，照片只在裝置記憶體處理、不上傳。
 */
import wasmUrl from 'onnxruntime-web/ort-wasm-simd-threaded.wasm?url'
import detUrl from '@/assets/ocr/ppocr-v5-mobile-det.onnx?url'
import recUrl from '@/assets/ocr/ppocr-v5-mobile-rec.onnx?url'
import dictionary from '@/assets/ocr/ppocr-v5-dict.txt?raw'
import { joinOcrRows, parsePrescriptionText, type OcrBox } from '@/utils/prescriptionText'

export interface OcrProgress {
  percent: number
  message: string
}

export type OcrEngineName = 'PaddleOCR'

/** 調整影像尺寸供辨識；小圖放大（最多 3 倍）明顯提高中文辨識率。處理後影像只存在裝置記憶體。 */
async function prepareImage(file: File, upscale = true): Promise<HTMLCanvasElement> {
  const url = URL.createObjectURL(file)
  try {
    const image = new Image()
    image.src = url
    await image.decode()
    const longest = Math.max(image.naturalWidth, image.naturalHeight)
    if (!longest) throw new Error('照片無法讀取，請重新選擇。')
    const scale = upscale ? Math.min(3, Math.max(1400, Math.min(2400, longest)) / longest) : 1
    const canvas = document.createElement('canvas')
    canvas.width = Math.max(1, Math.round(image.naturalWidth * scale))
    canvas.height = Math.max(1, Math.round(image.naturalHeight * scale))
    const context = canvas.getContext('2d')
    if (!context) throw new Error('無法讀取照片，請改用其他瀏覽器。')
    context.fillStyle = '#fff'
    context.fillRect(0, 0, canvas.width, canvas.height)
    context.imageSmoothingQuality = 'high'
    context.drawImage(image, 0, 0, canvas.width, canvas.height)
    return canvas
  } finally {
    URL.revokeObjectURL(url)
  }
}

/** 下載模型並回報進度（約 21 MB；瀏覽器快取後第二次起很快）。 */
async function download(url: string, onRatio: (ratio: number) => void): Promise<Uint8Array> {
  const response = await fetch(url)
  if (!response.ok) throw new Error('辨識模型下載失敗，請確認網路後重試。')
  const total = Number(response.headers.get('content-length')) || 0
  if (!response.body || !total) return new Uint8Array(await response.arrayBuffer())
  const reader = response.body.getReader()
  const chunks: Uint8Array[] = []
  let loaded = 0
  for (;;) {
    const { done, value } = await reader.read()
    if (done) break
    chunks.push(value)
    loaded += value.length
    onRatio(Math.min(1, loaded / total))
  }
  const data = new Uint8Array(loaded)
  let offset = 0
  for (const chunk of chunks) {
    data.set(chunk, offset)
    offset += chunk.length
  }
  return data
}

type Engine = Awaited<ReturnType<typeof import('esearch-ocr')['init']>>

// 模型載入一次後在整個網頁共用，避免每次進入拍照頁重新下載與初始化。
let pendingEngine: Promise<Engine> | null = null
let reportLoad: (ratio: number) => void = () => undefined
let reportRec: (done: number, total: number) => void = () => undefined

function getEngine(): Promise<Engine> {
  if (!pendingEngine) {
    pendingEngine = (async () => {
      const [ocr, ort] = await Promise.all([import('esearch-ocr'), import('onnxruntime-web/wasm')])
      ort.env.wasm.wasmPaths = { wasm: wasmUrl }
      // 沒有 cross-origin isolation 時無法多執行緒，明確設為單執行緒避免警告。
      ort.env.wasm.numThreads = 1
      // 沒有 cross-origin isolation 時瀏覽器不提供 SharedArrayBuffer，esearch-ocr 的 `instanceof SharedArrayBuffer`
      // 會丟 ReferenceError；補一個空的類別（沒有物件屬於它），只讓型別檢查不出錯。
      const scope = globalThis as { SharedArrayBuffer?: unknown }
      if (typeof scope.SharedArrayBuffer === 'undefined') scope.SharedArrayBuffer = class SharedArrayBufferUnavailable {}
      const sizes = [4.7, 16.5]
      const ratios = [0, 0]
      const progress = (index: number) => (ratio: number) => {
        ratios[index] = ratio
        reportLoad((ratios[0] * sizes[0] + ratios[1] * sizes[1]) / (sizes[0] + sizes[1]))
      }
      const [det, rec] = await Promise.all([download(detUrl, progress(0)), download(recUrl, progress(1))])
      return ocr.init({
        det: { input: det },
        rec: {
          input: rec,
          decodeDic: dictionary,
          // v5 模型英文空格已改善，需關閉額外補空格
          optimize: { space: false },
          on: (index, _result, total) => reportRec(index + 1, total),
        },
        ort: ort as unknown as Parameters<typeof ocr.init>[0]['ort'],
      })
    })()
    pendingEngine.catch(() => { pendingEngine = null })
  }
  return pendingEngine
}

/** 每個拍照頁建立一個辨識器；離開頁面時 dispose 會中止尚未完成的辨識。 */
export function createPrescriptionRecognizer(
  onProgress: (progress: OcrProgress) => void,
  /** 開發用：解析欄位前先回傳 OCR 原始文字與使用的辨識引擎，解析失敗時也能檢查辨識內容。 */
  onText?: (text: string, engine: OcrEngineName) => void,
) {
  let disposed = false
  let retrying = false
  let cancel: ((error: Error) => void) | null = null

  const cancelled = () => new DOMException('已取消辨識', 'AbortError')
  const report = (progress: OcrProgress) => { if (!disposed) onProgress(progress) }

  async function readText(engine: Engine, image: HTMLCanvasElement) {
    const { src } = await engine.ocr(image)
    if (disposed) throw cancelled()
    const { text, confidence } = joinOcrRows(src as OcrBox[])
    onText?.(text, 'PaddleOCR')
    return { text, confidence }
  }

  async function read(file: File) {
    retrying = false
    report({ percent: 0, message: '正在讀取照片…' })
    const image = await prepareImage(file)
    if (disposed) throw cancelled()
    reportLoad = (ratio) => report({ percent: Math.round(ratio * 40), message: '正在準備辨識，請稍候…' })
    reportRec = (done, total) => report({
      percent: Math.round((retrying ? 70 : 45) + (done / total) * 25),
      message: '正在辨識照片…',
    })
    const engine = await getEngine()
    if (disposed) throw cancelled()
    report({ percent: 45, message: '正在辨識照片…' })
    let { text, confidence } = await readText(engine, image)
    let result
    try {
      result = parsePrescriptionText(text, confidence)
    } catch {
      // 放大後偶爾反而失去細節；解析失敗時以原尺寸再辨識一次。
      retrying = true
      report({ percent: 70, message: '正在重新讀取照片…' })
      ;({ text, confidence } = await readText(engine, await prepareImage(file, false)))
      result = parsePrescriptionText(text, confidence)
    }
    report({ percent: 100, message: '正在整理藥單…' })
    return result
  }

  async function recognize(file: File) {
    if (disposed) throw cancelled()
    if (cancel) throw new Error('照片正在辨識中，請稍候。')
    let timeout: number | undefined
    const interrupted = new Promise<never>((_, reject) => {
      cancel = reject
      timeout = window.setTimeout(() => reject(new Error('辨識時間較長，請確認網路或換一張清楚的照片後重試。')), 120_000)
    })
    try {
      return await Promise.race([read(file), interrupted])
    } catch (e) {
      console.error('[prescription OCR]', e) // 保留原始錯誤，避免被下方通用訊息蓋掉
      if (e instanceof DOMException || (e instanceof Error && /照片|辨識|網路/.test(e.message))) throw e
      throw new Error('照片辨識失敗，請確認網路後重試，或重新選擇清楚的照片。')
    } finally {
      window.clearTimeout(timeout)
      cancel = null
    }
  }

  function dispose() {
    disposed = true
    cancel?.(cancelled())
    reportLoad = () => undefined
    reportRec = () => undefined
  }

  return { recognize, dispose }
}
