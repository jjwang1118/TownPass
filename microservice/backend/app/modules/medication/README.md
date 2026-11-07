# medication — 藥單與藥品

UI E02～E08、E06m、F03、F05：新增藥單的三條路徑（拍照辨識、掃藥袋 QR、手動）、確認藥單、加入完成、我的藥單、今天四個時段、首頁「下一次吃藥」。規格書 §5.2、§5.3、§8.1、§8.3。

**狀態**：✅ 完成（測試：`tests/test_medication.py`、`tests/test_rules.py`）

## 概念

- **藥單**：一個藥袋一張，用字母標示（A、B…）。長輩在實體藥袋上寫上大大的字母。吃藥中的藥單字母不重複；吃完（或提早移到「已吃完」）後字母釋放。
- **藥的編號**：字母＋序號，例如 A1、A2。
- **時段**：固定四個，早上 09:00、中午 12:00、晚上 18:00、睡前 22:00，不能修改。每個藥可以選很多個時段；飯前、飯後只是標示。
- **還剩幾天**（和前端 `utils/supply.ts` 相同）：剩下顆數 ÷ 每天吃幾顆，每個藥各自算；剩下顆數 = 總顆數 − 每天吃幾顆 × 從看診日過了幾天。沒有總顆數時用藥單天數推算。藥單的還剩幾天、吃完日取最晚吃完的藥；全部吃完後自動移到「已吃完」。
- **藥袋 QR 格式**：前後端共用 `docs/qrcode_format.md`（`hospital`、`medicines`、中文時段、`quantity`，選填 `lic` 健保碼、`doctor`）；舊的 v1、v2 仍可掃。

## 新增藥單：三條路徑 → 預覽 → 核對 → 加入

```
拍照：App 裝置端模型整理欄位 ─▶ POST /prescriptions/photo-preview ─┐
掃 QR：App qr_code_scan     ─▶ POST /prescriptions/qr-preview    ─┼─▶ 確認藥單（逐項核對、紅框不確定的欄位）
手動：藥名搜尋 /drugs/search ─▶ POST /prescriptions/preview       ─┘        │  修改後可再呼叫 /prescriptions/preview
                                                                              ▼
                                                     POST /prescriptions（配字母、記錄核對者）─▶ 加入完成
```

三個預覽 API 回同一個格式（`PreviewOut`），不寫入：

| 欄位 | 用途 |
|---|---|
| `letter` | 加入後會配的字母 |
| `draft` | 藥單草稿；核對、修改後送回 `POST /prescriptions` |
| `items` | 每個藥的編號（A1）、時段與時間、飯前飯後、同成分警示、`uncertain`（電腦不確定這一項）與 `uncertain_fields` |
| `uncertain` | 拍照辨識沒把握的欄位與信心分數（例如 `items.1.name`）；QR、手動為空 |
| `warnings` | 同成分警示（`code` 和 `with_code` 成分相同） |
| `schedule` | 四個時段各吃哪幾號（加入完成頁） |

**拍照辨識**：後端不跑模型（比賽規定 AI 推論在裝置端）。App 送來整理好的欄位，後端用健保碼或藥名比對健保藥品資料（容許錯字，相似度 0.75 以上才帶入代號與劑量），每個欄位的信心分數取「模型的把握」與「比對相似度」較低者，低於 0.8 列入 `uncertain`。看不出來的欄位先填預設值（一次 1 顆、早上、飯後、看診日為今天）；天數看不出來時為 null，加入前必須填。

**藥名搜尋**（手動新增、修改藥品）：打 2 個字以上，中英文都可以、不分大小寫、比對字首（產品名、中文名、主成分）。同藥名只出現一次，`strengths` 列出可選劑量，每個劑量帶一個健保藥品代號；只有 1 種時前端自動選好。北市聯醫常用藥（模擬，`rules.COMMON_ATC`）排前面、口服劑型排在注射與外用前面，最多 8 筆。

**同成分警示**：同一個健保藥品代號，或 ATC 7 碼（`drug_licenses.ingredients`）相同時標示「這兩包好像是同一種藥，請問藥師」。和吃藥中的藥、以及同一張藥單裡前面的藥比對。只標示，不阻擋。

**同時新增**：用 PostgreSQL advisory lock 鎖住同一位長輩，避免拿到同一個字母。

## API

| 方法 | 路徑 | 權限 | 說明 |
|---|---|---|---|
| GET | `/drugs/search?q=` | 登入 | 藥名搜尋 |
| POST | `/elders/{elder_id}/prescriptions/qr-preview` | 寫 | body 為 App 的 `qr_code_scan` 回覆 |
| POST | `/elders/{elder_id}/prescriptions/photo-preview` | 寫 | body 為 `PhotoIn`（規格書 §8.3） |
| POST | `/elders/{elder_id}/prescriptions/preview` | 寫 | body 為藥單草稿（手動、修改後再看一次） |
| POST | `/elders/{elder_id}/prescriptions` | 寫 | 加入；回藥單、警示、`schedule`、「請用筆在這個藥袋上寫一個大大的「A」…」 |
| GET | `/elders/{elder_id}/prescriptions?status=active\|finished` | 讀 | 吃藥中（依字母）、已吃完（新的在前） |
| GET | `/elders/{elder_id}/prescriptions/{id}` | 讀 | 藥單詳細 |
| PATCH | `/elders/{elder_id}/prescriptions/{id}` | 寫 | 補填院區、科別、醫師，或修改看診日、天數 |
| POST | `/elders/{elder_id}/prescriptions/{id}/finish` | 寫 | 移到「已吃完」，字母釋放；重複呼叫不會出錯 |
| GET | `/elders/{elder_id}/medications/{id}` | 讀 | 藥品詳細 |
| PATCH | `/elders/{elder_id}/medications/{id}` | 寫 | 修改藥名、代號、劑量、用途、顆數、時段、飯前飯後、待核對 |
| POST | `/elders/{elder_id}/medications/{id}/stop` | 寫 | body `{"reason": "finished" \| "doctor_advised"}`；重複停用不會出錯 |
| GET | `/elders/{elder_id}/today?date=` | 讀 | 今天四個時段的藥，依藥單分組，附朗讀稿；沒有藥的時段不列出 |
| GET | `/elders/{elder_id}/next-dose` | 讀 | 下一次吃藥的時段、時間與藥；沒有時回 `null` |

權限由 `FamilyService.ensure_access()` 檢查：長輩本人、尚未完成初始設定的家人可寫；其他綁定家人唯讀。

## 朗讀稿

由 [speech](../speech/README.md) 模組產生：

- 每個藥的「念給我聽」（`MedicationOut.speech_text`）：「1 號藥，脈優錠５毫克，心臟內科開的，降血壓。一次 1 顆，飯後吃，早上 9 點。還剩 23 天。」藥名有中文就念中文（先查健保中文品名）。
- 時段的「唸給我聽」（`TodaySlot.speech_text`，UI E02）：「中午 12 點，要吃新陳代謝科 1 號 1 顆、2 號 1 顆」。依藥單分組、用科別區分，不念英文字母與藥名；沒有科別時念「另一包藥」。

## 錯誤

| code | HTTP | 情況 |
|---|---|---|
| `QR_EMPTY` | 400 | 使用者取消掃描 |
| `QR_INVALID` | 400 | 不是藥袋 QR、版本不支援、缺欄位、藥沒有時段 |
| `DAYS_REQUIRED` | 400 | 加入時藥品沒有總顆數、藥單也沒有天數 |
| `PRESCRIPTION_NOT_FOUND`、`MEDICATION_NOT_FOUND` | 404 | 找不到 |
| `MEDICATION_STOPPED` | 409 | 修改已停用、或藥單已吃完的藥 |
| `TOO_MANY_PRESCRIPTIONS` | 409 | 吃藥中的藥單 A～Z 都用完 |
| `READ_ONLY`、`NOT_BOUND` | 403 | 見 family 模組 |

## 檔案

- `rules.py`：固定時段、頻率換時段、字母、吃完日、剩餘天數、同成分、推播用的「B1、B2 各 1 顆」、藥名搜尋與比對、北市聯醫常用藥（模擬）
- `schemas.py`：`RxQrPayload`（v2，一張藥單多個藥）、`RxQrPayloadV1`（舊版仍可掃）、`PhotoIn`、`PrescriptionDraft`、`PreviewOut`

## 資料表

- `prescriptions`：藥單；吃藥中的 `(elder_id, letter)` 不可重複；過了天數在查詢或新增時自動改為 `finished`
- `medications`：藥單裡的藥，`(prescription_id, seq)` 不可重複；`slots` 為時段陣列；停用時記錄 `stop_reason`
- `drug_licenses`：健保用藥品項，只讀（`seed/` 匯入全部 4.5 萬筆，見 `integrations/fda/`）

## 提供給其他模組（呼叫端自行檢查權限）

| 方法 | 給誰 | 回傳 |
|---|---|---|
| `list_active_doses(elder_id, day)` | 救命卡 | 這天在用藥期間內的藥（A1 等） |
| `slot_view(elder_id, slot_key, day)` | 吃藥提醒 | 某天某時段要吃的藥（依藥單分組）與朗讀稿；沒有藥時為 None |
| `last_visit(elder_id)` | 回診預約 | 最近看診的吃藥中藥單：字母、院區、科別、醫師 |
| `elders_scheduled_on(day)` | 提醒排程 | 這天有藥要吃的長輩 |
| `running_out_on(day)` | 回診提醒 | 在這天吃完的藥單，依長輩分組 |
| `soonest_run_out(elder_id)` | Demo | 最快吃完的那幾張藥單 |

## 依賴

- `family`：權限檢查
- `speech`：朗讀稿
- `integrations/townpass`：`QRCodeScanReply`
- `integrations/fda`：字串正規化（藥名比對）
