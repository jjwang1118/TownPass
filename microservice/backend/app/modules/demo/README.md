# demo — 展示用 API

Demo 時不用等到真的時間，立即觸發提醒與通知。**只在 `DEMO_MODE=true` 時掛載，正式版移除。** 規格書 §11.2。

**狀態**：待實作（API 回 501）

## API

| 方法 | 路徑 | 說明 |
|---|---|---|
| POST | `/demo/trigger/reminder?elder_id=` | 立即觸發吃藥提醒 |
| POST | `/demo/trigger/no-response?elder_id=` | 立即觸發「沒有回應」通知家人 |
| POST | `/demo/trigger/refill?elder_id=` | 立即觸發回診提醒 |

只有 `router.py`，實作時直接呼叫 `reminder` 等模組的 service。
