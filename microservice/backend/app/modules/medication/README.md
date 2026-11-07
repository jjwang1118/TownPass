# medication — 藥品與時段

功能規格「一、藥」1-1～1-4：我的藥、掃藥袋 QR 新增、藥品詳細頁、提醒時間設定，以及首頁狀態列「下一次吃藥」。規格書 §5.3、§8.1。

**狀態**：✅ 完成（測試：`tests/test_medication.py`、`tests/test_rules.py`）

本期新增藥品只有「掃藥袋 QR」；帶入聯醫用藥、手動輸入列為下一期。

## API

前綴都是 `/elders/{elder_id}`。

| 方法 | 路徑 | 權限 | 說明 |
|---|---|---|---|
| GET | `/medications?include_stopped=false` | 讀 | 藥品清單，依編號排序 |
| POST | `/medications/qr-preview` | 寫 | body 為 App 的 `qr_code_scan` 回覆；回確認畫面內容，不寫入 |
| POST | `/medications` | 寫 | body 為 preview 回傳的 `draft`（長輩核對後原樣送回） |
| GET | `/medications/{id}` | 讀 | 詳細頁 |
| PATCH | `/medications/{id}` | 寫 | 編輯用途、顆數、頻率、飯前飯後、開始日期、天數 |
| POST | `/medications/{id}/stop` | 寫 | body `{"reason": "finished" \| "doctor_advised"}`；重複停用不會出錯 |
| GET | `/time-slots` | 讀 | 7 個時段，第一次查詢時建立預設值 |
| PUT | `/time-slots` | 寫 | 只送要改的時段 |
| GET | `/next-dose` | 讀 | 下一次吃藥的時段、時間與藥；沒有時回 `null` |

權限由 `FamilyService.ensure_access()` 檢查：長輩本人、尚未完成初始設定的家人可寫；其他綁定家人唯讀。

## 新增藥品的流程

```
App qr_code_scan ─▶ POST qr-preview ─▶ 確認畫面（核對藥名、劑量、頻率）─▶ POST medications
                     回 draft、時段、警示                                   回編號、「請在藥袋上寫上大大的 N」
```

- **編號**：進行中藥品沒用到的最小正整數。停用後編號釋放。同時新增時用 PostgreSQL advisory lock 避免重複。
- **同成分警示**：同一個健保藥品代號，或 ATC 7 碼（`drug_licenses.ingredients`）相同時，回 `warnings`：「這兩包好像是同一種藥，請問藥師」。只標示，不阻擋。

## 藥卡內容（MedicationOut）

| 欄位 | 用途 |
|---|---|
| `number` | 大編號 |
| `name`、`dose_qty` | 藥名、一次幾顆（JSON 數字，可為 0.5） |
| `slots` | 時段、標籤與實際時間，例如 `早餐飯後 08:00` |
| `days_left`、`run_out_date` | 還剩幾天、吃完日 |
| `speech_text` | 「念給我聽」國語朗讀稿，例如「1 號藥，家醫科開的，降血壓。一次 1 顆，飯後吃，早上 8 點。還剩 19 天。」 |

依交付規格，朗讀稿**不唸英文字母**，所以不含藥名。台語由前端用預錄句子拼接，所需的編號、科別、用途、顆數、時間都在回應欄位中。

## 錯誤

| code | HTTP | 情況 |
|---|---|---|
| `QR_EMPTY` | 400 | 使用者取消掃描 |
| `QR_INVALID` | 400 | 不是藥袋 QR、版本不支援或缺欄位 |
| `DUPLICATE_SLOT` | 400 | 同一個時段送了兩次 |
| `MEDICATION_NOT_FOUND` | 404 | 找不到藥品 |
| `MEDICATION_STOPPED` | 409 | 修改已停用的藥 |
| `READ_ONLY`、`NOT_BOUND` | 403 | 見 family 模組 |

## 檔案

- `rules.py`：預設時段、頻率分配到時段、吃完日、剩餘天數、編號、同成分判斷、朗讀稿
- `schemas.py`：`RxQrPayload` 是藥袋 QR 的格式

## 資料表

- `medications`：進行中的藥，`(elder_id, number)` 不可重複；停用時記錄 `stop_reason`
- `time_slots`：每位長輩 7 筆
- `drug_licenses`：健保用藥品項，只讀（`seed/` 匯入全部 4.5 萬筆，見 `integrations/fda/`）

## 提供給其他模組（呼叫端自行檢查權限）

| 方法 | 給誰 | 回傳 |
|---|---|---|
| `list_active_doses(elder_id, day)` | 救命卡 | 這天在用藥期間內的進行中藥品 |
| `doses_for_slot(elder_id, slot_key, day)` | 提醒 | 某天某時段要吃的藥 |
| `slot_times(elder_id)` | 提醒 | 7 個時段的時間 |
| `last_visit(elder_id)` | 回診預約 | 最近一次開藥的院區、科別、醫師（同一天開的藥取最後加入的） |
| `elders_scheduled_on(day)` | 提醒排程 | 這天有藥要吃的長輩 |
| `running_out_on(day)` | 回診提醒 | 在這天吃完的藥，依長輩分組 |
| `soonest_run_out(elder_id)` | Demo | 最快吃完的那幾號藥 |

## 依賴

- `family`：權限檢查
- `integrations/townpass`：`QRCodeScanReply`
