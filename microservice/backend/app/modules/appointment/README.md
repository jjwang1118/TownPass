# appointment — 回診預約（Bonus）

UI E10～E12、E16、F08：預約回診（限聯合醫院）、預約成功、我的預約、回診前一天提醒。交付規格第 8 點（下拉選單）。比賽用模擬門診資料，正式上線再串接聯醫掛號系統。

**狀態**：✅ 完成（測試：`tests/test_appointment.py`）

## 步驟

| 步驟 | API | 說明 |
|---|---|---|
| 選院區（E10d） | `GET /hospitals` | 聯醫 7 院區共 9 筆：和平婦幼、林森中醫昆明各有 2 個院址，分開列出（如「和平婦幼院區（婦幼）」），附地址；「帶我去醫院」的 `launch_map` 才會導到正確地址 |
| 選科別（E10e） | `GET /hospitals/{id}/departments?elder_id=` | 帶 `elder_id` 時，最近看診的吃藥中藥單的科別排第一，標記 `last_visited` 與 `from_letter`（「藥單 A 的科別」） |
| 選醫師（E10b） | `GET /departments/{id}/doctors?elder_id=` | `schedule`：每週門診時間（「週一、週五 上午」）；2 週內每個看診時間都額滿或停診時 `available=false`、`note=已額滿`；藥單上的醫師排第一並標記，前端預設選取 |
| 選日期（E10f） | `GET /doctors/{id}/sessions` | 這位醫師明天起 2 週的門診：`label`「11/14（五）」、`period_label`「上午門診」；額滿、停診 `available=false`，`note` 為「已額滿」「停診」 |
| 選時段（E10g） | `GET /sessions/{id}/slots` | 每個看診時間：`label`「上午 09:30」、`remaining` 剩餘名額、`note`「還有 3 個名額」「已額滿」 |
| 確認預約（E11） | `POST /elders/{elder_id}/appointments` | body `{"slot_id"}`；回預約成功頁內容 |

更換前一步的選擇時，後面的選擇要清空（前端處理，交付規格第 8 點）。

## 預約成功與我的預約

| 方法 | 路徑 | 說明 |
|---|---|---|
| GET | `/elders/{elder_id}/appointments` | 我的預約：今天以後、未取消，依日期與時間排序 |
| POST | `/elders/{elder_id}/appointments/{id}/cancel` | 取消；重複取消不會出錯；看診日已過不能取消 |

預約成功頁（AppointmentOut）：看診號碼 `visit_no`、`date_label`、`time_label`、院區（含 `map`）、科別、醫師、`message`「回診前一天，您和家屬都會收到提醒。」

預約、取消的權限：長輩本人，或尚未完成初始設定的家人；查看我的預約：長輩或任何綁定家人。

## 規則

- **不超額**：佔名額用一條 `UPDATE clinic_slots … WHERE booked_count < capacity … RETURNING`，同時搶最後一個名額只有一人成功。
- **看診號碼不重複**：取消會釋出名額（`booked_count - 1`），但號碼由門診只增不減的 `issued_count` 發出。模擬資料有預先填入的預約，所以號碼不一定從 1 號開始。
- **同一門診不能重複預約**（即使選不同時間）：部分唯一索引 `(elder_id, session_id) WHERE status = 'booked'`。
- **可預約期間**：明天起 14 天內。

## 回診前一天提醒（由 internal 模組的 `/internal/tick` 呼叫）

`send_reminders(now)`：每一筆有效預約，前一天 18:00 起自動推播一次，不需要「加入提醒」。長輩與家屬的文字不同：

| 對象 | 標題｜內文 |
|---|---|
| 長輩（E16） | 明天 09:30 要回診｜仁愛院區心臟內科林醫師，記得帶健保卡 |
| 家屬（F08） | 王美玉 明天 09:30 要回診｜仁愛院區心臟內科林醫師，記得提醒或陪伴她 |

`data.map` 為「帶我去醫院」的 `launch_map` 訊息。用 `UPDATE … RETURNING` 領取，重複呼叫不會重複推播。

## 錯誤

| code | HTTP | 情況 |
|---|---|---|
| `HOSPITAL_NOT_FOUND`、`DEPARTMENT_NOT_FOUND`、`DOCTOR_NOT_FOUND`、`SESSION_NOT_FOUND`、`SLOT_NOT_FOUND`、`APPOINTMENT_NOT_FOUND` | 404 | 找不到 |
| `ALREADY_BOOKED` | 409 | 已經預約過這個門診 |
| `SLOT_FULL` | 409 | 這個時間已額滿 |
| `SESSION_SUSPENDED` | 409 | 停診 |
| `SESSION_OUT_OF_RANGE` | 409 | 不在明天起 2 週內 |
| `APPOINTMENT_PAST` | 409 | 看診日已過，不能取消 |
| `READ_ONLY`、`NOT_BOUND` | 403 | 見 family 模組 |

## 檔案

- `rules.py`：可預約期間、看診時間（每 30 分鐘一個）、日期與時間文字、每週門診時間、提醒文字

## 資料表

- `hospitals`、`departments`、`doctors`、`clinic_sessions`、`clinic_slots`：模擬門診與看診時間（`seed/` 匯入）
- `appointments`：預約紀錄（門診、看診時間、看診號碼）

## 依賴

- `medication`：最近藥單的字母、院區、科別、醫師（`last_visit`）
- `family`：權限、要通知的家屬
- `emergency_card`：長輩的姓名與性別（家屬推播）
- `notification`：推播
- `integrations/townpass`：`LaunchMapMessage`
- `integrations/tpech`：正式版改由聯醫查詢門診
