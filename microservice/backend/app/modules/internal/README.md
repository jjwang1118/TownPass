# internal — 排程入口

排程的入口。本地部署由**後端內建排程**（`scheduler.py`）每分鐘執行一次 `TickService`；`POST /internal/tick` 保留給手動測試。規格書 §6.1。

**狀態**：✅ 完成（吃藥提醒、回診提醒、預約提醒）

## API

| 方法 | 路徑 | 說明 |
|---|---|---|
| POST | `/internal/tick` | 需要 `X-Internal-Secret` header（值為 `INTERNAL_SECRET`）；不出現在 API 文件 |

回應：`{"created": 1, "refill": 0, "appointment": 0}`，分別是新建立的吃藥提醒（長輩與家屬同時推播）、回診提醒（藥單快吃完）、預約提醒（前一天 18:00）的數量。

手動觸發（`INTERNAL_SECRET` 在 `.env`）：

```bash
curl -X POST http://localhost:8000/api/v1/internal/tick -H "X-Internal-Secret: dev-internal-secret"
```

## 檔案

- `scheduler.py`：內建排程，後端啟動時開始（`SCHEDULER_ENABLED=true`），對齊每分鐘第 1 秒執行；單次失敗只記 log，不影響下一分鐘
- `router.py`：手動觸發的 API，驗證 `X-Internal-Secret`
- `service.py`：`TickService` 依序呼叫各模組的排程工作，本身沒有業務規則；`TickResult` 定義回應格式

## 依賴

- `reminder`：吃藥提醒、回診提醒
- `appointment`：預約提醒
