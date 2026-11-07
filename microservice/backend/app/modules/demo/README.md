# demo — 展示用 API

Demo 時不用等到真正的時間，立即觸發提醒與通知。**只在 `DEMO_MODE=true` 時掛載，正式版移除。** 規格書 §11.2。

**狀態**：✅ 完成（測試：`tests/test_reminder.py` 的 `test_demo_triggers`）

## API

需要登入（長輩或綁定的家人），`elder_id` 放在 query string。

| 方法 | 路徑 | 說明 |
|---|---|---|
| POST | `/demo/trigger/reminder?elder_id=` | 立即提醒今天第一個有藥的時段；今天已提醒過就重新開始（次數歸零） |
| POST | `/demo/trigger/no-response?elder_id=` | 把最近一筆未回應的提醒當作 3 次沒回應，立即通知家人（沒有未回應的提醒時先觸發一筆） |
| POST | `/demo/trigger/refill?elder_id=` | 立即發回診提醒，提醒最快吃完的那幾號藥 |

只有 `router.py`，實際邏輯在 `reminder` 模組的 `demo_trigger_*` 方法。

## Demo 建議順序

1. 長輩掃範例藥袋 QR 加入藥品（`seed/qr/`）
2. 家人用邀請碼綁定，並在手機登記推播
3. `trigger/reminder`：長輩手機跳出吃藥提醒
4. `trigger/no-response`：家人收到「媽媽 08:00 的吃藥提醒沒有回應，要不要打給她？」
5. `trigger/refill`：長輩和家人收到回診提醒
