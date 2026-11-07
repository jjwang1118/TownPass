# app/integrations/fcm/

Firebase Cloud Messaging，伺服器推播到長輩和家人的手機。規格書 §2.1、§6.2。

| 檔案 | 內容 |
|---|---|
| `client.py` | `PushMessage`、`Pusher` 介面、`LogPusher`、`FcmPusher`、`get_pusher()` |

- 沒有設定 `FIREBASE_CREDENTIALS`：使用 `LogPusher`，推播內容只印在 log，方便本機開發。
- 有設定：使用 `FcmPusher` 真的發送。
- 其他模組不要直接用這裡，請呼叫 `notification` 模組的 `NotificationService.push()`，由它查出使用者的裝置 token。

狀態：✅ 完成。實際送到手機需要 App 端加上 `firebase_messaging` 與 `push_token` Handler。
