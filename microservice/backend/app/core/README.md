# app/core/

各模組共用、**沒有業務規則**的基礎設施。業務規則放在 `modules/`。

| 檔案 | 內容 | 常用的東西 |
|---|---|---|
| `config.py` | 讀取環境變數（`.env`）；連線字串自動轉成 asyncpg 格式；在雲端（Render）啟動前檢查金鑰 | `get_settings()`、`cors_origins`、`production_problems()` |
| `db.py` | 資料庫連線、ORM 基底 | `Base`、`UUIDPrimaryKey`、`CreatedAt`、`Timestamps`、`enum_column()`、`get_session()` |
| `deps.py` | 共用的 FastAPI `Depends` | `SessionDep`、`CurrentUserId`（長輩、家人）、`ResponderClaims`（救護人員） |
| `errors.py` | 業務錯誤與錯誤回應格式 | 見下表 |
| `security.py` | JWT、密碼雜湊、欄位加密 | `issue_token()`、`hash_password()`、`EncryptedText`、`EncryptedJSON` |
| `clock.py` | 取得現在時間 | `now()`（UTC）、`today_taipei()`、`TAIPEI` |

## 業務錯誤

service 只丟這些錯誤，不 import FastAPI。回應格式為 `{"error": {"code", "message"}}`。

| 類別 | HTTP | 預設 code |
|---|---|---|
| `ValidationFailed` | 400 | `VALIDATION_ERROR`（輸入格式錯誤也會轉成這個） |
| `Unauthorized` | 401 | `UNAUTHORIZED` |
| `Forbidden` | 403 | `FORBIDDEN` |
| `NotFound` | 404 | `NOT_FOUND` |
| `Conflict` | 409 | `CONFLICT` |
| `TooManyRequests` | 429 | `TOO_MANY_REQUESTS` |
| `NotImplementedYet` | 501 | `NOT_IMPLEMENTED`（尚未實作的 service 方法） |

需要更明確的 code 時：`raise Conflict("邀請碼已使用", code="INVITE_USED")`。

## 注意

- 時間一律用 `clock.now()`，不要直接呼叫 `datetime.now()`，之後測試才能替換時間。
- 個資欄位（電話、病史、過敏）用 `EncryptedText` 或 `EncryptedJSON`，需要 `.env` 的 `FIELD_ENCRYPTION_KEY`。
