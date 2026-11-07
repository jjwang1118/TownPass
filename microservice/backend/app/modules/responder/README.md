# responder — 救護人員

救護人員用消防局帳號登入，掃 QR 或輸入卡號查看救命卡。規格書 §3、§7.2。

**狀態**：待實作（API 回 501）

## API

| 方法 | 路徑 | 說明 |
|---|---|---|
| POST | `/responder/login` | 比對名冊，在職且有救護權限才發 token（12 小時） |
| POST | `/responder/cards/lookup` | body：`qr`（App 的 `qr_code_scan` 回覆）或 `code` 擇一，加上 `location`（App 的 `location` 回覆） |

## 規則

- 每次請求都重新確認名冊，離職立即失效。
- 只能看，不能修改。
- 每人每分鐘最多查詢 10 次，避免猜卡號。

## 資料表

- `responders`：模擬名冊（EMT-001～003）

## 依賴

- `emergency_card`：`lookup_for_responder()`
- `integrations/fire_dept`：名冊（正式版）
- `integrations/townpass`：`QRCodeScanReply`、`LocationReply`
