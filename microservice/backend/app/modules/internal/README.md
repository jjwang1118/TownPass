# internal — 排程入口

免費主機沒有請求時會休眠，程式內的排程器不可靠，所以由 cron-job.org 每分鐘呼叫一次 `/internal/tick`（同時讓 Render 不休眠）。規格書 §6.1、`docs/deploy.md` 步驟 5。

**狀態**：✅ 完成（吃藥提醒、回診提醒、預約提醒）

## API

| 方法 | 路徑 | 說明 |
|---|---|---|
| POST | `/internal/tick` | 需要 `X-Internal-Secret` header（值為 `INTERNAL_SECRET`）；不出現在 API 文件 |

回應：`{"created": 1, "repushed": 0, "escalated": 0, "refill": 0, "appointment": 0}`，分別是新建立的吃藥提醒、重新提醒、通知家人沒有回應、回診提醒（藥快吃完）、預約提醒的數量。

本機手動觸發：

```bash
curl -X POST http://localhost:8000/api/v1/internal/tick -H "X-Internal-Secret: dev-internal-secret"
```

## 檔案

- `router.py`：驗證呼叫者
- `service.py`：`TickService` 依序呼叫各模組的排程工作，本身沒有業務規則；`TickResult` 定義回應格式

## 待加入

- 正式版可改為簽章驗證，或限制呼叫來源 IP

## 依賴

- `reminder`：吃藥提醒、回診提醒
- `appointment`：預約提醒
