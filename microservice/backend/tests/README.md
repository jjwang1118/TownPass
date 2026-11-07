# tests/

自動測試。在 `microservice/backend` 執行 `uv run pytest`。

| 檔案 | 內容 | 需要資料庫 |
|---|---|---|
| `conftest.py` | 共用設定：測試資料庫、`api`、`login`、`sessionmaker` fixture | — |
| `test_townpass_messages.py` | 讀 App 的 `account.json` 和 handler 原始碼，確認後端格式和 App 一致 | 否 |
| `test_rules.py` | 時段分配、剩餘天數、編號、朗讀稿、同成分、卡號等純計算 | 否 |
| `test_app.py` | 路由、錯誤格式、登入檢查；資料表能編譯成 PostgreSQL | 否 |
| `test_family.py` | 邀請碼、綁定、權限檢查 | 是 |
| `test_medication.py` | 掃藥袋 QR、編號、同成分警示、藥卡、停用、時段、下一次吃藥、家人權限 | 是 |
| `test_emergency_card.py` | 救命卡、同意、卡號、救護人員登入與查詢、通知家人、完整 Demo 流程 | 是 |
| `test_reminder.py` | 時段提醒、再提醒 3 次、通知家人、回應、提醒家人、回診提醒、Demo 觸發 | 是 |
| `test_appointment.py` | 6 步驟預約、上次科別醫師排第一、額滿停診、看診號碼、搶最後名額、我的預約、取消、預約提醒 | 是 |

## 資料庫

- 需要資料庫的測試使用獨立的 `chiah_ioh_lo_test`，不會動到開發用的資料。第一次執行時自動建立。
- 每次執行會重建資料表，每個測試結束後清空資料。
- PostgreSQL 沒啟動時這些測試會**略過**（顯示 `s`），先執行 `docker compose up -d`。
- 要用別的資料庫：設定環境變數 `TEST_DATABASE_URL`。

## 跨平台

組內有人用 Windows，寫程式時注意：

- **讀寫檔案一律指定 `encoding="utf-8"`**。Windows 繁體中文環境預設是 Big5（cp950），讀到含中文的檔案會出錯。
- **時區用 `app.core.clock.TAIPEI`**。Windows 沒有內建時區資料，靠 `tzdata` 套件提供，不要從依賴中移除。

在 Mac 或 Linux 上模擬 Windows 的這兩個條件來跑測試：

```bash
PYTHONTZPATH= LC_ALL=zh_TW.Big5 PYTHONUTF8=0 uv run pytest
```

## 寫新測試

| fixture | 用途 |
|---|---|
| `api` | 連到測試資料庫的 `httpx.AsyncClient` |
| `login` | `await login("townpass-id", "姓名", "elder")` 用 App 模擬帳號登入並選身分，回傳 `(headers, user_id)` |
| `sessionmaker` | 直接呼叫 service 時開 session：`async with sessionmaker() as session:` |
| `pushes` | 取代 FCM，發出的推播記在 `pushes.sent`，可檢查內容 |

- 測試函式可以直接寫 `async def`（已設定 `asyncio_mode = "auto"`）。
- 不需要資料庫的 API 測試參考 `test_app.py`。
- 固定現在時間：`monkeypatch.setattr(clock, "now", lambda: ...)`，參考 `test_medication.py` 的 `freeze()`。
