# app/integrations/fcm/

Firebase Cloud Messaging，伺服器推播到長輩和家人的手機。規格書 §2.1、§6.2。

| 檔案 | 內容 |
|---|---|
| `client.py` | `PushMessage`、`Pusher` 介面、`LogPusher`、`FcmPusher`、`get_pusher()` |

- 沒有設定 `FIREBASE_CREDENTIALS`：使用 `LogPusher`，推播內容只印在 log，方便本機開發。
- 其他值：Firebase 服務帳戶金鑰，可以是 JSON 內容（直接貼進環境變數）或 JSON 檔路徑（Render Secret File，見 `docs/deploy.md` 步驟 6）。
- firebase-admin 是同步 API，發送時放到背景執行緒，避免卡住其他請求。
- 其他模組不要直接用這裡，請呼叫 `notification` 模組的 `NotificationService.push()`，由它查出使用者的裝置 token。

狀態：✅ 完成。實際送到手機需要 App 端加上 `firebase_messaging` 與 `push_token` Handler。
