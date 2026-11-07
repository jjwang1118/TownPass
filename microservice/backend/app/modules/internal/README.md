# internal — 排程入口

Cloud Run 沒有請求時會關機，程式內的排程器不可靠，所以由 Cloud Scheduler 每分鐘呼叫一次 `/internal/tick`。規格書 §6.1。

**狀態**：待實作（會呼叫 `reminder` 的方法，目前回 501）

## API

| 方法 | 路徑 | 說明 |
|---|---|---|
| POST | `/internal/tick` | 需要 `X-Internal-Secret` header；不出現在 API 文件 |

## 檔案

- `router.py`：驗證呼叫者
- `service.py`：`TickService` 依序呼叫各模組的排程工作，本身沒有業務規則

## 待加入的工作

- 回診提醒：每天 09:00，藥再 7 天吃完
- 預約提醒：前一天 18:00、當天 08:00

## 依賴

- `reminder`、`appointment`
