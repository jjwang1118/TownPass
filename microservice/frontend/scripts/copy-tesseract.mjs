/**
 * 拍藥袋 OCR：把 tesseract.js 的 worker、核心（WebAssembly）與繁中、英文字庫複製到 public/tesseract/，
 * 和前端一起部署，執行時不向 CDN 下載（比賽規定推論在裝置端，評審可能關閉網路測試）。
 *
 * npm run dev／npm run build 前會自動執行（package.json 的 predev、prebuild）。
 * 字庫用 4.0.0_best_int（只有 LSTM、整數量化，檔案小、適合手機）。
 */
import { copyFileSync, mkdirSync, readdirSync } from 'node:fs'
import { dirname, join } from 'node:path'
import { fileURLToPath } from 'node:url'

const root = join(dirname(fileURLToPath(import.meta.url)), '..')
const modules = join(root, 'node_modules')
const out = join(root, 'public', 'tesseract')

function copy(from, to) {
  mkdirSync(dirname(to), { recursive: true })
  copyFileSync(from, to)
}

copy(join(modules, 'tesseract.js', 'dist', 'worker.min.js'), join(out, 'worker.min.js'))

// 只複製 LSTM 版本的核心；tesseract.js 會依瀏覽器是否支援 SIMD 自動挑一個
const core = join(modules, 'tesseract.js-core')
for (const file of readdirSync(core).filter((f) => /^tesseract-core.*-lstm\.wasm\.js$/.test(f))) {
  copy(join(core, file), join(out, 'core', file))
}

for (const lang of ['chi_tra', 'eng']) {
  const file = `${lang}.traineddata.gz`
  copy(join(modules, '@tesseract.js-data', lang, '4.0.0_best_int', file), join(out, 'lang', file))
}

console.log(`tesseract：已複製到 ${out}`)
