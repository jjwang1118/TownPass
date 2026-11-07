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
│   ├── integrations/     外部系統：城市通 App、北市聯醫、消防局、健保用藥品項、FCM
│   └── modules/          功能模組：auth、family、medication、reminder…
├── alembic/              資料表變更（migration）
│   └── versions/         每一次變更一個檔案
├── seed/                 Demo 用種子資料與範例藥袋 QR
├── tests/                自動測試
├── scripts/              小工具（建立 .env 並產生金鑰）
├── secrets/              Firebase 服務帳戶金鑰（自己建立，不 commit）
├── pyproject.toml        套件與工具設定（uv 管理）
├── uv.lock               鎖定的套件版本，要 commit
├── alembic.ini           Alembic 設定
├── compose.yaml          本地部署：資料庫（預設）＋後端（--profile app）
├── Dockerfile            後端映像檔
├── .env.example          環境變數範本（scripts.init_env 會複製成 .env，.env 不 commit）
└── .dockerignore         不打包進映像檔的檔案（含金鑰檔）
```

## 啟動

需要 [uv](https://docs.astral.sh/uv/) 與 Docker。第一次先建立 `.env`（會產生加密金鑰）：

```bash
cd microservice/backend
uv sync                               # 安裝套件（Python 3.12）
uv run python -m scripts.init_env     # 建立 .env
```

**Demo（全部用 Docker）**：資料庫＋後端，啟動時自動更新資料表、匯入範例資料、啟動內建排程。

```bash
docker compose --profile app up -d --build
```

**開發（改程式即時生效）**：Docker 只跑資料庫，後端用 uv 跑。

```bash
docker compose up -d                  # 只啟動資料庫
uv run alembic upgrade head           # 建立或更新資料表
uv run python -m seed.load            # 匯入範例資料（產生之後 2 週的門診）
uv run uvicorn app.main:app --reload  # 啟動後端（內建排程也會啟動）
```

兩種方式不要同時開，都會佔用 port 8000。Android 模擬器裡用 `http://10.0.2.2:8000` 連後端。完整說明見 [../docs/deploy.md](../docs/deploy.md)。

- API 文件：<http://localhost:8000/docs>
- 測試：`uv run pytest`

**Windows**：以上指令在 PowerShell 都可以直接執行。台北時區資料由 `tzdata` 套件提供，不需要另外安裝。下方 curl 範例用到 bash 語法，請在 Git Bash 執行，或改用 Swagger。

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

## 部署

比賽不能使用付費服務，所以採本地部署：資料庫與後端用 Docker 跑在一台電腦上，Demo 用 Android Studio 模擬器；推播用 Firebase 免費方案（選用）。完整步驟見 [../docs/deploy.md](../docs/deploy.md)。
