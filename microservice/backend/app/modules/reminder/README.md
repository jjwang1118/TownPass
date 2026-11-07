# reminder — 吃藥提醒

UI E09（長輩收到的推播）、F04（家屬收到的推播）、E03／F05（點開後的時段用藥詳情），功能規格 3-1（回診提醒）。規格書 §6。

**狀態**：✅ 完成（測試：`tests/test_reminder.py`）

## 流程

```
09:00、12:00、18:00、22:00 時段到（這個時段有藥）
   ├─▶ 長輩：「中午 12:00 該吃藥了｜B1、B2 各 1 顆，點開可以聽語音」
   └─▶ 所有綁定家屬（同時）：「王美玉 中午 12:00 該吃藥了｜B1、B2 各 1 顆，記得關心她」
```

- 每個時段只推播一次，不再提醒，也不需要長輩回應。
- 排程延誤超過 30 分鐘就不補發，避免長輩在錯的時間被提醒。
- 已停用的藥、已吃完的藥單、還沒開始或已過天數的藥不會提醒。

## API

| 方法 | 路徑 | 誰可以用 | 說明 |
|---|---|---|---|
| GET | `/reminders/{event_id}` | 長輩、綁定家人 | 點開推播後的時段用藥詳情 |
| GET | `/elders/{elder_id}/reminders?date=` | 長輩、綁定家人 | 某天的提醒 |
| POST | `/elders/{elder_id}/nudge` | 綁定家人 | 家人提醒長輩吃藥：「陳小美提醒你吃藥喔」 |

## 時段用藥詳情（ReminderOut）

| 欄位 | 用途 |
|---|---|
| `label`、`scheduled_at` | 「中午 12:00 要吃的藥」 |
| `groups` | 依藥單分組：字母、院區、科別、每個藥（編號、藥名、劑量、顆數、用途、飯前飯後） |
| `items` | 所有藥攤平 |
| `speech_text` | 「唸給我聽」：「中午 12 點，要吃新陳代謝科 1 號 1 顆、2 號 1 顆」（不念英文字母與藥名，見 [speech](../speech/README.md)） |
| `speech_text_en` | 英文朗讀稿（給外籍看護） |
| `elder_name` | 救命卡上的姓名；還沒建立救命卡時用台北通姓名 |

藥品內容是建立提醒時的快照（`groups`），之後改藥不影響這筆紀錄。

## 推播

| type | 對象 | 標題｜內文 | data |
|---|---|---|---|
| `medication_reminder` | 長輩 | 中午 12:00 該吃藥了｜B1、B2 各 1 顆，點開可以聽語音 | `event_id`、`deeplink` |
| `family_medication_reminder` | 所有綁定家屬 | 王美玉 中午 12:00 該吃藥了｜B1、B2 各 1 顆，記得關心她 | `event_id`、`deeplink` |
| `medication_nudge` | 長輩 | 家人提醒｜陳小美提醒你吃藥喔 | 最近一筆提醒的 `event_id`（有的話） |
| `refill_reminder` | 長輩、所有綁定家屬 | 回診提醒｜藥單 A（仁愛院區 心臟內科）再 7 天就吃完囉，要記得回診或領慢箋 | |

顆數不同時寫成「A1 1 顆、C1 半顆」。「她／他」依救命卡上的性別。

## 排程（由 internal 模組呼叫）

| 方法 | 做什麼 |
|---|---|
| `create_due_events` | 時段到了（30 分鐘內），建立提醒並同時推播長輩與家屬 |
| `send_refill_reminders` | 每天 09:00 起，藥單再 7 天吃完時提醒長輩與家屬 |

建立用一條 SQL 完成（`INSERT … ON CONFLICT DO NOTHING RETURNING`），排程同時跑兩次也只會推播一次。

## Demo（只在 `DEMO_MODE`，由 demo 模組呼叫）

`demo_trigger_reminder`、`demo_trigger_refill`，見 `demo/README.md`。

## 錯誤

| code | HTTP | 情況 |
|---|---|---|
| `REMINDER_NOT_FOUND` | 404 | 找不到提醒 |
| `FAMILY_ONLY` | 403 | 長輩要用「提醒長輩吃藥」 |
| `NOT_BOUND` | 403 | 沒有綁定這位長輩 |

## 檔案

- `rules.py`：時間窗、推播文字

## 資料表

- `reminder_events`：每位長輩、每個時段、每天最多一筆；`groups` 存當下的藥品快照
- `refill_notices`：回診提醒發送紀錄（`letters`），同一個吃完日只發一次

## 依賴

- `medication`：要吃的藥（依藥單分組）、快吃完的藥單
- `family`：權限、要通知的家屬
- `emergency_card`：長輩的姓名與性別
- `speech`：朗讀稿
