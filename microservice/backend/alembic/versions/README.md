# alembic/versions/

每次資料表變更一個檔案，檔名為 `日期_版本號_說明.py`，依 `down_revision` 串成順序。

| 檔案 | 內容 |
|---|---|
| `20261107_f9fea4f23ad7_init.py` | 第一版：建立全部 19 張資料表 |
| `20261107_621183e5af7e_medication_stop_reason.py` | `medications` 新增停用原因 `stop_reason` |
| `20261107_e60c934e0318_responder_unit_phone_access_log_snapshot.py` | `responders` 新增分隊電話；`card_access_logs` 新增救護人員姓名、分隊快照 |
| `20261107_70c6a238747c_reminder_scheduled_date_refill_notices.py` | `reminder_events` 改以台北日期判斷重複；新增 `refill_notices` |
| `20261107_d4b4f0542791_appointment_booking.py` | `clinic_sessions` 新增 `issued_count`；`appointments` 新增取消時間、加入提醒、提醒紀錄與防重複預約索引 |
| `20261108_f6497e343c3a_prescriptions_and_ui_alignment.py` | 依 UI 調整：新增藥單 `prescriptions`、重建 `medications`、`reminder_events`、`refill_notices`，移除 `time_slots`；救命卡改為姓名、出生年月日、血型；新增看診時間 `clinic_slots`；藥品資料加搜尋欄位。**無法降版**；會清空門診與預約（模擬資料，啟動時重新匯入） |

產生與套用方式見 [../README.md](../README.md)。
