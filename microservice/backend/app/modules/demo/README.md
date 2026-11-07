# demo — 展示用 API

Demo 時不用等到真正的時間，立即觸發提醒與通知。**只在 `DEMO_MODE=true` 時掛載，正式版移除。** 規格書 §11.2。

**狀態**：✅ 完成（測試：`tests/test_reminder.py` 的 `test_demo_triggers`）

## API

需要登入（長輩或綁定的家人），`elder_id` 放在 query string。

| 方法 | 路徑 | 說明 |
|---|---|---|
| POST | `/demo/trigger/reminder?elder_id=` | 立即提醒今天第一個有藥的時段，長輩與家屬同時收到；今天已提醒過就再推播一次 |
| POST | `/demo/trigger/refill?elder_id=` | 立即發回診提醒，提醒最快吃完的那幾張藥單；回 `{"letters": ["A"]}` |

只有 `router.py`，實際邏輯在 `reminder` 模組的 `demo_trigger_*` 方法。

## Demo 建議順序

1. 長輩掃範例藥袋 QR 加入藥單 A、B（`seed/qr/`）；再掃藥單 C 示範同成分警示
2. 家人用邀請碼綁定，並在手機登記推播
3. `trigger/reminder`：長輩手機跳出「早上 09:00 該吃藥了」，女兒手機同時收到「王美玉 早上 09:00 該吃藥了」
4. `trigger/refill`：長輩和家人收到回診提醒
