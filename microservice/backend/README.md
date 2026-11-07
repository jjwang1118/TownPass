# 呷藥囉 後端

FastAPI + PostgreSQL。完整規格見 [../docs/backend-spec.md](../docs/backend-spec.md)。

## 目錄

每個目錄都有自己的 README，說明那一層放什麼。

```
backend/
├── app/                  程式碼主體 → app/README.md
│   ├── main.py           建立 FastAPI、掛載所有模組
│   ├── models.py         匯入所有 ORM 模型（給 Alembic 用）
│   ├── core/             共用基礎：設定、資料庫、認證、加密、錯誤
│   ├── integrations/     外部系統：城市通 App、北市聯醫、消防局、食藥署、FCM
│   └── modules/          功能模組：auth、family、medication、reminder…
├── alembic/              資料表變更（migration）
│   └── versions/         每一次變更一個檔案
├── seed/                 Demo 用種子資料
├── tests/                自動測試
├── pyproject.toml        套件與工具設定（uv 管理）
├── uv.lock               鎖定的套件版本，要 commit
├── alembic.ini           Alembic 設定
├── compose.yaml          本機 PostgreSQL
├── Dockerfile            Cloud Run 部署用
├── .env.example          環境變數範本（複製成 .env，.env 不 commit）
└── .dockerignore
```

## 本機開發

需要 [uv](https://docs.astral.sh/uv/) 與 Docker。

```bash
cd microservice/backend
cp .env.example .env          # 填入 JWT_SECRET、FIELD_ENCRYPTION_KEY（產生方式見檔內說明）
uv sync                       # 安裝套件（Python 3.12）
docker compose up -d          # 啟動本機 PostgreSQL
uv run alembic upgrade head   # 建立或更新資料表

uv run uvicorn app.main:app --reload
```

- API 文件：<http://localhost:8000/docs>
- 測試：`uv run pytest`

修改 `models.py` 後，產生新的 migration 並檢查內容再 commit，見 [alembic/README.md](alembic/README.md)。

## 不用前端也能開發與測試

後端只收 HTTP JSON，前端還沒做好時可以這樣測：

1. **Swagger**：開 <http://localhost:8000/docs>，直接在網頁上呼叫 API。
2. **Postman**：入門指引建議的工具，適合存下常用的請求和隊友共用。
3. **pytest**：用 `httpx` 直接呼叫 API，見 [tests/README.md](tests/README.md)。

模擬 App 的回覆時，照 App 的 `{ name, data }` 格式送即可。例如登入：

```bash
curl -X POST http://localhost:8000/api/v1/auth/townpass \
  -H 'Content-Type: application/json' \
  -d "{\"name\":\"userinfo\",\"data\":$(jq .data ../../assets/mock_data/account.json)}"
```

回應中的 `access_token` 放進之後請求的 `Authorization: Bearer <token>`。

**只有這些需要 App 或前端才能測**：推播實際送到手機、全螢幕提醒、國台語朗讀、掃描實體 QR。沒有設定 `FIREBASE_CREDENTIALS` 時，推播內容會印在後端 log，可以先確認內容正確。

## 與城市通 App 的溝通

後端不直接和 App 溝通，格式定義在 [app/integrations/townpass/](app/integrations/townpass/)：

- **App → 後端**：前端把 App 的回覆 `JSON.parse(event.data)` 後，原封不動放進 request body。
- **後端 → App**：回應中的 `call`、`map` 等欄位是完整的 `{ name, data }`，前端直接
  `window.flutterObject.postMessage(JSON.stringify(...))`。

## 部署（Cloud Run）

```bash
gcloud run deploy chiah-ioh-lo-api --source . --region asia-east1
```

環境變數見規格書 §10。
