# responder — 救護人員

功能規格 2-4：救護人員用消防局帳號登入，掃敬老卡背面 QR 或輸入卡號查看救命卡。

**狀態**：✅ 完成（測試：`tests/test_emergency_card.py`）

## API

| 方法 | 路徑 | 說明 |
|---|---|---|
| POST | `/responder/login` | 比對消防局名冊，在職且有救護權限才發 token（12 小時，一個勤務班） |
| POST | `/responder/cards/lookup` | body：`qr`（App 的 `qr_code_scan` 回覆）或 `code`（手動輸入）擇一，加上 `location`（App 的 `location` 回覆，可省略） |

查詢範例：

```json
{
  "qr": { "name": "qr_code_scan", "data": "https://<前端網址>/c/TPE-7K3Q-9X2M" },
  "location": { "name": "location", "data": { "latitude": 25.0478, "longitude": 121.5171, "timestamp": 1762500000000 } }
}
```

## 規則

- 帳號不分大小寫。帳號不存在和密碼錯誤回同樣的錯誤，不透露有哪些帳號。
- 每次查詢都重新確認名冊：登入後才離職或被取消權限，也會立即失效。
- 只能查看，沒有修改的 API。
- 手動輸入卡號時忽略大小寫、空白、連字號。
- 每人每分鐘最多查詢 10 次（`rate_limit.py`），避免猜卡號。次數記在伺服器記憶體。
- 路人用一般相機掃到 QR 會開啟前端公開頁，只顯示「請撥打 119」，**不呼叫後端**。

## 錯誤

| code | HTTP | 情況 |
|---|---|---|
| `INVALID_CREDENTIALS` | 401 | 帳號或密碼錯誤 |
| `RESPONDER_NOT_AUTHORIZED` | 403 | 「無權限」：已離職或沒有救護權限 |
| `CARD_CODE_INVALID` | 400 | 不是救命卡 QR，或卡號格式不對 |
| `CARD_NOT_FOUND` | 404 | 卡號無效或已重新產生 |
| `RATE_LIMITED` | 429 | 查詢太頻繁 |

## 檔案

- `rate_limit.py`：查詢次數限制

## 資料表

- `responders`：模擬消防局名冊（帳號、密碼雜湊、姓名、分隊、分隊電話、職稱、在職狀態、救護權限）。範例帳號見 `seed/README.md`。

## 依賴

- `emergency_card`：`lookup_for_responder()`、卡號規則
- `integrations/townpass`：`QRCodeScanReply`、`LocationReply`
- `integrations/fire_dept`：正式版改由消防局名冊查詢
