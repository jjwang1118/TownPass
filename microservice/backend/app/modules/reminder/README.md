# reminder — 吃藥提醒

時間到推播長輩；沒回應就每 10 分鐘再提醒，3 次都沒回應就通知家人。規格書 §6。

**狀態**：待實作（API 回 501）

## API

| 方法 | 路徑 | 說明 |
|---|---|---|
| GET | `/reminders/{event_id}` | 提醒畫面資料：稱呼、時段、幾號吃幾顆 |
| POST | `/reminders/{event_id}/ack` | 長輩按「好，我知道了」 |
| GET | `/elders/{elder_id}/reminders?date=` | 某天的提醒與回應狀態 |
| POST | `/elders/{elder_id}/nudge` | 家人提醒長輩吃藥 |

## 給排程呼叫

由 `internal` 模組的 `/internal/tick` 每分鐘呼叫，每項都要可以重複執行而不重複發送：

- `create_due_events()`：時段到了，建立提醒並推播
- `repush_unacked()`：沒回應，再推播
- `escalate_no_response()`：3 次沒回應，通知家人

## 資料表

- `reminder_events`：每位長輩每個時段每天一筆；`items` 存當下的藥品快照

## 依賴

- `medication`：該時段要吃的藥
- `family`：權限、要通知的家人
- `notification`：推播
