# appointment — 回診預約（Bonus）

功能規格 3-2（預約回診，限聯合醫院）、3-3（我的預約），交付規格第 8 點（下拉選單）。比賽用模擬門診資料，正式上線再串接聯醫掛號系統。

**狀態**：✅ 完成（測試：`tests/test_appointment.py`）

## 6 個步驟

| 步驟 | API | 說明 |
|---|---|---|
| 1 選院區 | `GET /hospitals` | 聯醫 7 院區共 9 筆：和平婦幼、林森中醫昆明各有 2 個院址，分開列出（如「和平婦幼院區（婦幼）」），「帶我去醫院」的 `launch_map` 才會導到正確地址 |
| 2 選科別 | `GET /hospitals/{id}/departments?elder_id=` | 帶 `elder_id` 時，藥區「上次看的科別」排第一並標記 `last_visited` |
| 3 選醫師 | `GET /departments/{id}/doctors?elder_id=` | 上次看診的醫師排第一並標記，前端預設選取 |
| 4 選日期 | `GET /doctors/{id}/sessions` | 只列這位醫師明天起 2 週有門診的日子，`label` 如「11/12（星期三）」 |
| 5 選時段 | （同上，每天的 `sessions`） | 上午、下午、晚上；`available=false`（額滿、停診）顯示灰色不可選 |
| 6 確認 | `POST /elders/{elder_id}/appointments` | body `{"session_id"}`；回完成頁內容 |

更換前一步的選擇時，後面的選擇要清空（前端處理，交付規格第 8 點）。

## 完成頁與我的預約

| 方法 | 路徑 | 說明 |
|---|---|---|
| PUT | `/elders/{elder_id}/appointments/{id}/reminder` | 「加入提醒」：body `{"enabled": true}`；前一天 18:00、當天 08:00 推播長輩與家人 |
| GET | `/elders/{elder_id}/appointments` | 我的預約：今天以後、未取消，依日期排序 |
| POST | `/elders/{elder_id}/appointments/{id}/cancel` | 取消；重複取消不會出錯；看診日已過不能取消 |

完成頁（AppointmentOut）：院區（含 `map`）、科別、醫師、`date_label`、`period_label`、看診號碼 `visit_no`、`reminder_enabled`。

預約、取消、加入提醒的權限：長輩本人，或尚未完成初始設定的家人；查看我的預約：長輩或任何綁定家人。

## 規則

- **不超額**：佔名額與發號碼用一條 `UPDATE … WHERE booked_count < capacity … RETURNING`，同時搶最後一個名額只有一人成功。
- **看診號碼不重複**：取消會釋出名額（`booked_count - 1`），但號碼由只增不減的 `issued_count` 發出。
- **同一門診不能重複預約**：部分唯一索引 `(elder_id, session_id) WHERE status = 'booked'`。
- **可預約期間**：明天起 14 天內。

## 預約提醒（由 internal 模組的 `/internal/tick` 呼叫）

`send_reminders(now)`：有「加入提醒」的預約，前一天 18:00 起、當天 08:00 起各推播一次：

> 明天晚上 仁愛院區 家醫科 林醫師 回診，看診號碼 1 號

`data.map` 為「帶我去醫院」的 `launch_map` 訊息。用 `UPDATE … RETURNING` 領取，重複呼叫不會重複推播。

## 錯誤

| code | HTTP | 情況 |
|---|---|---|
| `HOSPITAL_NOT_FOUND`、`DEPARTMENT_NOT_FOUND`、`DOCTOR_NOT_FOUND`、`SESSION_NOT_FOUND`、`APPOINTMENT_NOT_FOUND` | 404 | 找不到 |
| `ALREADY_BOOKED` | 409 | 已經預約過這個門診 |
| `SESSION_FULL` | 409 | 額滿 |
| `SESSION_SUSPENDED` | 409 | 停診 |
| `SESSION_OUT_OF_RANGE` | 409 | 不在明天起 2 週內 |
| `APPOINTMENT_PAST` | 409 | 看診日已過，不能取消 |
| `APPOINTMENT_CANCELLED` | 409 | 已取消的預約不能加入提醒 |
| `READ_ONLY`、`NOT_BOUND` | 403 | 見 family 模組 |

## 檔案

- `rules.py`：可預約期間、日期與時段文字、提醒文字

## 資料表

- `hospitals`、`departments`、`doctors`、`clinic_sessions`：模擬門診（`seed/` 匯入）
- `appointments`：預約紀錄

## 依賴

- `medication`：上次看的院區、科別、醫師（`last_visit`）
- `family`：權限、要通知的家人
- `notification`：推播
- `integrations/townpass`：`LaunchMapMessage`
- `integrations/tpech`：正式版改由聯醫查詢門診
