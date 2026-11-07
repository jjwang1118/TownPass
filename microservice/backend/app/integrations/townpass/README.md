# app/integrations/townpass/

城市通 App 與微服務網頁之間的訊息格式。完全依照《城市通入門指引》第 03 章與 App 原始碼 `lib/util/web_message_handler/`。規格書 §2.3。

| 檔案 | 內容 |
|---|---|
| `messages.py` | 訊息名稱與每種訊息的 schema |

## 規則

- **App → 後端**：前端把 App 的回覆 `JSON.parse(event.data)` 後原封不動送到後端。`*Reply` 類別逐欄對照 App 實際回傳的格式，**不可以改欄位名稱**。
- **後端 → App**：`*Message` 類別是完整的 `{ name, data }`，放在 API 回應裡，前端直接 `postMessage(JSON.stringify(...))`。

## 訊息

| 類別 | name | 方向 | 對照的 App 程式碼 |
|---|---|---|---|
| `UserinfoReply` | `userinfo` | App → 後端 | `lib/bean/account.dart` 的 `Account`；沒有帳號時 `data` 為 `[]`，視為錯誤 |
| `LocationReply` | `location` | App → 後端 | geolocator `Position.toJson()`；失敗時 `data` 為 `[]`，轉成 `None` |
| `QRCodeScanReply` | `qr_code_scan` | App → 後端 | 掃到的字串；取消時為 `null` |
| `PushTokenReply` | `push_token` | App → 後端 | 自訂 Handler（App 端尚未實作） |
| `PhoneCallMessage` | `phone_call` | 後端 → App | App 組成 `tel://{data}`，所以只保留數字與 `+` |
| `LaunchMapMessage` | `launch_map` | 後端 → App | `data` 為地圖網址 |
| `NotifyMessage` | `notify` | 前端 → App | 內容不可包含「已訂閱」「已取消訂閱」，否則 App 會改動訂閱清單 |

## 新增自訂訊息

1. 在 `CustomMessageName` 加上名稱。和 `BuiltinMessageName` 重複時，程式啟動會失敗。
2. 加上對應的 `*Reply` 或 `*Message` 類別。
3. App 端依入門指引新增 `TPWebMessageHandler`，並加入 `_cachedMessageHandlers`。

`tests/test_townpass_messages.py` 會讀 App 的模擬資料和 handler 原始碼確認格式一致，App 改版後重跑即可發現差異。
