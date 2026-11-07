# medication — 藥品與時段

藥品清單、掃藥袋 QR 新增、提醒時段設定。規格書 §5.3、§8.1。

**狀態**：待實作（API 回 501）；`rules.py` 已完成並有測試。

## API

前綴都是 `/elders/{elder_id}`。

| 方法 | 路徑 | 說明 |
|---|---|---|
| GET | `/medications` | 藥品清單（含時段、剩餘天數） |
| POST | `/medications/qr-preview` | body 為 App 的 `qr_code_scan` 回覆；回解析結果與同成分警示，不寫入 |
| POST | `/medications` | 確認後加入，回編號 |
| GET | `/medications/{id}` | 詳細頁 |
| PATCH | `/medications/{id}` | 編輯 |
| POST | `/medications/{id}/stop` | 停用（編號釋放） |
| GET | `/time-slots` | 7 個時段 |
| PUT | `/time-slots` | 修改時段 |
| GET | `/next-dose` | 首頁狀態列「下一次吃藥：今天 12:00」 |

## 檔案

- `rules.py`：預設時段、頻率分配到時段、吃完日、剩餘天數、下一個編號
- `schemas.py`：`RxQrPayload` 是藥袋 QR 的格式

## 資料表

- `medications`：進行中的藥，`(elder_id, number)` 不可重複
- `time_slots`：每位長輩 7 筆
- `drug_licenses`：食藥署資料，只讀

## 提供給其他模組

- `list_active_doses(elder_id)`：救命卡的「正在吃的藥」、提醒的內容

## 依賴

- `family`：權限檢查
- `integrations/townpass`：`QRCodeScanReply`
