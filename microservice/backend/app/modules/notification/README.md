# notification — 推播

登記手機的推播 token，並提供其他模組發送推播。規格書 §6.2。

**狀態**：✅ 完成

## API

| 方法 | 路徑 | 說明 |
|---|---|---|
| POST | `/devices` | body 為 App 的 `push_token` 回覆；同一個 token 換人登入時改綁 |
| DELETE | `/devices/{token}` | 移除 token |

## 提供給其他模組

`NotificationService.push(user_ids, type, title, body, data)`：查出使用者所有裝置並發送。不 commit，交由呼叫端的交易決定。

`type` 用 `schemas.PushType`，App 點開通知時依 `type` 導到對應頁面。

## 資料表

- `device_tokens`：一個使用者可以有多台裝置

## 依賴

- `integrations/fcm`：實際發送
- `integrations/townpass`：`PushTokenReply`
