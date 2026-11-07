# appointment — 回診預約（Bonus）

依序選院區 → 科別 → 醫師 → 日期 → 時段，再確認預約。限聯合醫院，比賽用模擬資料。規格書 §5.2。

**狀態**：待實作（API 回 501）

## API

| 方法 | 路徑 | 說明 |
|---|---|---|
| GET | `/hospitals` | 院區清單，附 `launch_map` 訊息（帶我去醫院） |
| GET | `/hospitals/{id}/departments?elder_id=` | 科別；上次看的排第一 |
| GET | `/departments/{id}/doctors?elder_id=` | 醫師；標記上次看診的醫師 |
| GET | `/doctors/{id}/sessions` | 未來 2 週門診；額滿、停診標示不可選 |
| POST | `/elders/{elder_id}/appointments` | 預約 |
| GET | `/elders/{elder_id}/appointments` | 我的預約 |
| POST | `/elders/{elder_id}/appointments/{id}/cancel` | 取消 |

## 資料表

- `hospitals`、`departments`、`doctors`、`clinic_sessions`：模擬門診資料
- `appointments`：預約紀錄

預約時用一條 `UPDATE … WHERE booked_count < capacity` 確保不超額。

## 依賴

- `medication`：上次看的科別、醫師
- `family`：權限
- `integrations/tpech`：聯醫（正式版）
