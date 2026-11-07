# alembic/versions/

每次資料表變更一個檔案，檔名為 `日期_版本號_說明.py`，依 `down_revision` 串成順序。

| 檔案 | 內容 |
|---|---|
| `20261107_f9fea4f23ad7_init.py` | 第一版：建立全部 19 張資料表 |
| `20261107_621183e5af7e_medication_stop_reason.py` | `medications` 新增停用原因 `stop_reason` |
| `20261107_e60c934e0318_responder_unit_phone_access_log_snapshot.py` | `responders` 新增分隊電話；`card_access_logs` 新增救護人員姓名、分隊快照 |
| `20261107_70c6a238747c_reminder_scheduled_date_refill_notices.py` | `reminder_events` 改以台北日期判斷重複；新增 `refill_notices` |

產生與套用方式見 [../README.md](../README.md)。
