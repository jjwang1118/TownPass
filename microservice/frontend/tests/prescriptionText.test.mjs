import assert from 'node:assert/strict'
import { readFileSync } from 'node:fs'
import test from 'node:test'
import vm from 'node:vm'
import ts from 'typescript'

const exports = {}
const source = readFileSync(new URL('../src/utils/prescriptionText.ts', import.meta.url), 'utf8')
vm.runInNewContext(ts.transpileModule(source, {
  compilerOptions: { module: ts.ModuleKind.CommonJS, target: ts.ScriptTarget.ES2020 },
}).outputText, { exports })
const parse = (text, confidence = 90) => JSON.parse(JSON.stringify(exports.parsePrescriptionText(text, confidence)))

test('相簿藥袋表格可讀取藥名、數量、民國日期與每八小時用法', () => {
  const result = parse(`範例診所\n就診日期:107.10.10\nDl-methylephedrine [內服] 1 9.0TB 3天 每八小時使用一次`)
  assert.equal(result.hospital, '範例診所')
  assert.equal(result.visit_date, '2018-10-10')
  assert.equal(result.days, 3)
  assert.equal(result.items[0].name, 'Dl-methylephedrine')
  assert.equal(result.items[0].dose_qty, 1)
  assert.equal(result.items[0].quantity, 9)
  assert.equal(result.items[0].frequency, 'TID')
  assert.equal(result.items[0].meal_timing, null)
  assert.ok(result.items[0].confidence.name < 0.8)
})

test('編號表格藥袋（PaddleOCR 實際輸出）：藥名與用量黏在一起、漏讀編號仍讀得到', () => {
  const result = parse([
    '日期： 114.05.17 身份：健保診 科别：01家馨科',
    '童品名用典骨型 款量 天数用洁 码烟上服用方店',
    'TOPIRAMATE100SG全 2.00 21 HS 42.0 睡前 一大部世：3',
    '2. CHLORFRONAZINE100MO2.00 21 ONOR 2.0',
    '6. ROSUVASTATIN SWG 1.00 ORSU52T.0 前一次',
    '8. 100',
    '16.CLCITRI0L25活维D1.0021 CCAL 21.0 每日早餐版',
    '17.TOPIRAVATE25MG時1.00 21 HS 0I0P321.0 医前一次',
    '内合：（18）第品警語與建議情示项目*',
  ].join('\n'))
  assert.deepEqual(result.items.map((item) => item.name), ['TOPIRAMATE100SG全', 'CHLORFRONAZINE100MO', 'ROSUVASTATIN SWG', 'CLCITRI0L25活维D', 'TOPIRAVATE25MG時'])
  assert.deepEqual(result.items.map((item) => item.dose_qty), [2, 2, 1, 1, 1])
  assert.equal(result.items[0].frequency, 'HS')
  assert.equal(result.items[4].strength, '25MG')
  // 天數與總量：用量後依序為天數、總量；超過一半的藥同為 21 天
  assert.equal(result.days, 21)
  // 最後一列簡碼黏住總量（0I0P321.0），超出合理範圍不採用
  assert.deepEqual(result.items.map((item) => item.quantity), [42, 2, null, 21, null])
})

test('編號表格藥袋：天數欄整欄漏讀時，仍讀得到每個藥的總量', () => {
  const result = parse([
    'TOPIRAMATE100MG全 2.00 HS CTOP1 42.0 睡前一次部位',
    'CHLORPRONAZINE 10OMG2.00 HS ONOR 42.0 通前',
    'ROSUVASTATIN SMG 1.00 ORSU5 21.0 前',
    '10. SENNOSIDE 12MG 3.00 QH 63.0',
  ].join('\n'))
  assert.equal(result.days, null)
  assert.deepEqual(result.items.map((item) => item.quantity), [42, 42, 21, 63])
})

test('編號表格藥袋：個別天數被 OCR 讀錯時，仍取多數藥品的天數', () => {
  const result = parse(['1. AAAAMINE 10MG 1.00 21 QD 21.0', '2. BBBBLOL 5MG 1.00 21 QD 21.0', '3. CCCCPAM 2MG 3.00 71 HS 63.0'].join('\n'))
  assert.equal(result.days, 21)
  assert.deepEqual(result.items.map((item) => item.quantity), [21, 21, 63])
})

test('只有藥名時不猜劑量、天數、用法或看診日', () => {
  const result = parse('藥名:測試藥品\n藥品費用:66點\n合計費用:483點')
  assert.equal(result.visit_date, null)
  assert.equal(result.days, null)
  assert.equal(result.items[0].dose_qty, null)
  assert.equal(result.items[0].quantity, null)
  assert.equal(result.items[0].frequency, null)
  assert.equal(result.items[0].meal_timing, null)
  assert.equal(result.items[0].confidence.dose_qty, 0)
})

test('標籤格式支援全形符號、中文空格與半顆', () => {
  const result = parse(`藥 名：測試藥 ５毫克\n每 次 用 量：半顆\n每日二次 飯後\n總顆數：１４\n給藥天數：１４`)
  assert.equal(result.items[0].name, '測試藥 5毫克')
  assert.equal(result.items[0].strength, '5毫克')
  assert.equal(result.items[0].dose_qty, 0.5)
  assert.equal(result.items[0].quantity, 14)
  assert.equal(result.items[0].frequency, 'BID')
  assert.equal(result.items[0].meal_timing, 'after')
  assert.equal(result.days, 14)
})

test('多個藥品保留各自用量，不將不同天數合成同一天數', () => {
  const result = parse(`Alpha 100mg [口服] 1 14錠 7天 BID 飯前\nBeta [內服] 0.5 3TB 3天 QD 飯後`)
  assert.equal(result.items.length, 2)
  assert.equal(result.items[0].quantity, 14)
  assert.equal(result.items[0].frequency, 'BID')
  assert.equal(result.items[0].meal_timing, 'before')
  assert.equal(result.items[1].quantity, 3)
  assert.equal(result.items[1].dose_qty, 0.5)
  assert.equal(result.items[1].frequency, 'QD')
  assert.equal(result.items[1].meal_timing, 'after')
  assert.equal(result.days, null)
})

test('無效日期、矛盾飯前飯後、不支援的頻率均保留待核對', () => {
  const result = parse(`藥名:測試藥\n看診日期:2026/02/30\n用法:Q4H 飯前或飯後`)
  assert.equal(result.visit_date, null)
  assert.equal(result.items[0].frequency, null)
  assert.equal(result.items[0].meal_timing, null)
})

test('不將無法表示的四分之一顆截斷成其他劑量', () => {
  const result = parse(`藥名:測試藥\n每次0.25顆`)
  assert.equal(result.items[0].dose_qty, null)
})

test('空白照片或只有費用資料時不建立模擬藥品', () => {
  assert.throws(() => parse(''), /找不到可辨識的藥名/)
  assert.throws(() => parse('藥品名稱 劑量 總量\n合計費用:483點'), /找不到可辨識的藥名/)
})

// PaddleOCR 文字框：[文字, 分數, 左, 上, 右, 下]；內容取自 scqa_drug_warning02 藥袋放大 3 倍的實際辨識結果
const box = ([text, mean, left, top, right, bottom]) => ({
  text, mean, box: [[left, top], [right, top], [right, bottom], [left, bottom]],
})
const PADDLE_SAMPLE = [
  ['醫聖模範診所（高雄市三民區德北街1號）', 0.92, 10, 40, 900, 70],
  ['院代：1111111111科别：01', 0.94, 10, 80, 560, 110],
  ['電话：07-3154932', 0.95, 600, 82, 900, 108],
  ['就诊日期：107.10.10', 0.94, 10, 160, 480, 190],
  ['醫師：郝醫師藥局地點：本院所調劑者：郝藥師藥師', 0.92, 10, 240, 1300, 270],
  ['9.0TB=3天每八小時使用一次', 0.95, 520, 362, 1380, 388],
  ['DI -me thy lephedrine [内股] 1', 0.88, 40, 360, 500, 390],
  ['適應症：支氣管氣喘、哥麻疹、過敏性疾患', 0.88, 10, 560, 1000, 590],
  ['', Number.NaN, 0, 0, 0, 0],
].map(box)

test('PaddleOCR 文字框依位置接回同一列，並由左至右排列', () => {
  const { text, confidence } = exports.joinOcrRows(PADDLE_SAMPLE)
  const lines = text.split('\n')
  assert.equal(lines[1], '院代：1111111111科别：01 電话：07-3154932')
  assert.equal(lines[4], 'DI -me thy lephedrine [内股] 1 9.0TB=3天每八小時使用一次')
  assert.ok(confidence > 90 && confidence < 100)
})

test('PaddleOCR 藥袋：簡體字轉繁體、接回斷開的藥名、醫師姓名不含後面欄位', () => {
  const { text, confidence } = exports.joinOcrRows(PADDLE_SAMPLE)
  const result = parse(text, confidence)
  assert.equal(result.hospital, '醫聖模範診所')
  assert.equal(result.department, '01')
  assert.equal(result.doctor, '郝醫師')
  assert.equal(result.visit_date, '2018-10-10')
  assert.equal(result.days, 3)
  assert.equal(result.items.length, 1)
  assert.equal(result.items[0].name, 'DI-methylephedrine')
  assert.equal(result.items[0].purpose, '支氣管氣喘、哥麻疹、過敏性疾患')
  assert.equal(result.items[0].dose_qty, 1)
  assert.equal(result.items[0].quantity, 9)
  assert.equal(result.items[0].frequency, 'TID')
  assert.equal(result.items[0].meal_timing, null)
  assert.ok(result.confidence.doctor < 0.8)
})

test('總量的 0 被辨識成 D 時仍讀得到；一般英文藥名不被誤接', () => {
  const result = parse('Amlodipine besylate 5 mg [口服] 1 28.DTB 28天 QD 飯后')
  assert.equal(result.items[0].name, 'Amlodipine besylate 5 mg')
  assert.equal(result.items[0].quantity, 28)
  assert.equal(result.items[0].meal_timing, 'after')
})
