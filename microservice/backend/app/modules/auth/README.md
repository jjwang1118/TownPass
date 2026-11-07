# auth — 台北通登入與身分

用 App 的 `userinfo` 回覆登入，第一次使用時選擇「我是長輩」或「我是家人」。規格書 §3。

**狀態**：✅ 完成

## API

| 方法 | 路徑 | 說明 |
|---|---|---|
| POST | `/auth/townpass` | body 為 App 的 `userinfo` 回覆；建立或更新使用者，回 JWT（7 天） |
| PUT | `/me/role` | 選擇身分；選過就不能改（`DEMO_MODE` 時可改） |
| GET | `/me` | 自己的資料與身分 |

## 資料表

- `users`：台北通 ID、身分、姓名、電話（加密）、出生年。不儲存身分證字號。

## 提供給其他模組

- `get_me(user_id)`：身分與姓名
- `get_profiles(user_ids)`：一次查多位使用者，回傳 `{user_id: MeOut}`

## 依賴

- `integrations/townpass`：`UserinfoReply`、`TownPassAccount`

## 注意

比賽時直接信任前端轉送的 userinfo；正式版需要伺服器端驗證（規格書 §13）。
