# app/

後端程式碼主體。

| 路徑 | 說明 |
|---|---|
| `main.py` | 建立 FastAPI：CORS、錯誤處理、把每個模組的 router 掛在 `/api/v1` 下；`DEMO_MODE` 時才掛 demo 模組。另有 `GET /health`（健康檢查，Render 的 Health Check Path） |
| `models.py` | 匯入所有模組的 `models.py`，讓 Alembic 看得到全部資料表。**新增模組時要加在這裡** |
| [core/](core/) | 各模組共用的基礎：設定、資料庫、認證、加密、錯誤 |
| [integrations/](integrations/) | 外部系統的介面：城市通 App、北市聯醫、消防局、食藥署、FCM |
| [modules/](modules/) | 功能模組，每個模組內分三層 |

## 依賴方向

```
modules/  ──▶  integrations/  ──▶  core/
   └──────────────────────────────▶  core/
```

- `core/` 不 import `modules/` 或 `integrations/`。
- `integrations/` 不 import `modules/`。
- 模組之間的規則見 [modules/README.md](modules/README.md)。
