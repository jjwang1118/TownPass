# reminder — 吃藥提醒

功能規格 1-5（吃藥提醒畫面）、1-6（家人）、3-1（回診提醒）。規格書 §6。

**狀態**：✅ 完成（測試：`tests/test_reminder.py`）

## 流程

```
08:00 時段到 ──▶ 推播長輩（第 1 次）
08:10 沒回應 ──▶ 再推播（第 2 次）
08:20 沒回應 ──▶ 再推播（第 3 次）
08:30 沒回應 ──▶ 通知家人「媽媽 08:00 的吃藥提醒沒有回應，要不要打給她？」＋撥給長輩

長輩按「好，我知道了」──▶ 停止提醒；有開啟回應通知的家人收到「媽媽已回應 08:00 的吃藥提醒」
```

- 間隔由 `REMIND_INTERVAL_MINUTES` 設定（預設 10 分鐘）。
- 家人**不會**在每個時段都收到提醒（功能規格 1-6：長輩回應時通知、3 次沒回應時通知）。
- 排程延誤超過 30 分鐘就不補發，避免長輩在錯的時間被提醒。
- 已停用或已過用藥天數的藥不會提醒。

## API

| 方法 | 路徑 | 誰可以用 | 說明 |
|---|---|---|---|
| GET | `/reminders/{event_id}` | 長輩、綁定家人 | 提醒畫面資料 |
| POST | `/reminders/{event_id}/ack` | **長輩本人** | 「好，我知道了」；重複按不會重複通知家人 |
| GET | `/elders/{elder_id}/reminders?date=` | 長輩、綁定家人 | 某天的提醒與回應狀態 |
| POST | `/elders/{elder_id}/nudge` | 綁定家人 | 家人提醒長輩吃藥：「陳小美提醒你吃藥喔」 |

## 提醒畫面（ReminderOut）

| 欄位 | 用途 |
|---|---|
| `items` | 大字顯示「1 號 → 2 顆」（`number`、`qty`） |
| `speech_text` | 自動朗讀：「陳阿嬤，吃藥時間到囉～飯後吃：1 號 脈優錠 2 顆、3 號 Metformin 500mg 1 顆」；藥名規則見 [speech](../speech/README.md) |
| `elder_title` | 救命卡上的稱呼；還沒建立救命卡時用台北通姓名 |
| `status` | `pending` 等待回應、`acked` 已回應、`no_response` 已通知家人 |

全螢幕、聲音、震動、閃光由 App 處理；國語朗讀用手機 TTS。英文、台語朗讀稿之後由 speech 模組加上。

## 推播

| type | 對象 | 內容 | data |
|---|---|---|---|
| `medication_reminder` | 長輩 | 同 `speech_text` | `event_id`、`deeplink` |
| `medication_acked` | 有開回應通知的家人 | 媽媽已回應 08:00 的吃藥提醒 | `event_id`、`deeplink` |
| `medication_no_response` | 所有綁定家人 | 媽媽 08:00 的吃藥提醒沒有回應，要不要打給她？ | `call`（撥給長輩的 `phone_call` 訊息） |
| `medication_nudge` | 長輩 | 陳小美提醒你吃藥喔 | 最近未回應的 `event_id`（有的話） |
| `refill_reminder` | 長輩、所有綁定家人 | 1 號、3 號的藥再 7 天就吃完囉，要記得回診或領慢箋 | |

「媽媽」是各家人綁定時設定的稱呼；「她／他」依救命卡上的性別。

## 排程（由 internal 模組呼叫）

`internal` 模組的 `TickService` 每分鐘依序呼叫以下方法，每項都可以重複執行而不重複發送：

| 方法 | 做什麼 |
|---|---|
| `create_due_events` | 時段到了（30 分鐘內），建立提醒並推播長輩 |
| `repush_unacked` | 沒回應且距上次推播滿間隔，再推播（最多 3 次） |
| `escalate_no_response` | 第 3 次後滿間隔仍沒回應，通知家人 |
| `send_refill_reminders` | 每天 09:00 起，藥再 7 天吃完時提醒長輩與家人 |

建立與領取都用一條 SQL 完成（`ON CONFLICT DO NOTHING RETURNING`、`UPDATE … RETURNING`），排程同時跑兩次也只會推播一次。

## Demo（只在 `DEMO_MODE`，由 demo 模組呼叫）

`demo_trigger_reminder`、`demo_trigger_no_response`、`demo_trigger_refill`，見 `demo/README.md`。

## 錯誤

| code | HTTP | 情況 |
|---|---|---|
| `REMINDER_NOT_FOUND` | 404 | 找不到提醒 |
| `ELDER_ONLY` | 403 | 家人要按「好，我知道了」 |
| `FAMILY_ONLY` | 403 | 長輩要用「提醒長輩吃藥」 |
| `NOT_BOUND` | 403 | 沒有綁定這位長輩 |

## 檔案

- `rules.py`：次數、間隔、時間窗、各種通知文字

## 資料表

- `reminder_events`：每位長輩、每個時段、每天最多一筆；`items` 存當下的藥品快照
- `refill_notices`：回診提醒發送紀錄，同一個吃完日只發一次

## 依賴

- `medication`：要吃的藥、時段、快吃完的藥
- `family`：權限、要通知的家人與稱呼
- `emergency_card`：長輩的稱呼與性別
- `auth`：長輩電話、家人姓名
- `notification`：推播
