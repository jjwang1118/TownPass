# 呷藥囉｜本地部署步驟

比賽規定不能使用付費服務，所以**全部跑在一台電腦上**：資料庫和後端用 Docker，App 用 Android Studio 的模擬器。唯一的線上服務是推播用的 Firebase 免費方案（不用綁卡；不設定也可以，推播內容會顯示在後端 log）。

```
┌──────────────────── 同一台電腦 ────────────────────┐
│                                                     │
│  Android 模擬器（長輩）─┐                            │
│  Android 模擬器（家人）─┼─ http://10.0.2.2:5173 ─▶ 前端網頁
│                        └─ http://10.0.2.2:8000 ─▶ 後端 API（Docker）
│                                                       │ 內建排程每分鐘檢查提醒
│                                                       ▼
│                                                  PostgreSQL（Docker）
└─────────────────────────────────────────────────────┘
        後端 ──推播──▶ Firebase Cloud Messaging（免費）──▶ 模擬器
```

> **`10.0.2.2` 是 Android 模擬器連到電腦本機的固定位址**。在模擬器裡用 `localhost` 會連到模擬器自己，不是電腦。

> 指令都在 `microservice/backend` 目錄執行，Windows（PowerShell）、Mac 都一樣。

---

## 0. 需要安裝

| 工具 | 用途 |
|---|---|
| [Docker Desktop](https://www.docker.com/products/docker-desktop/) | 跑資料庫與後端 |
| [uv](https://docs.astral.sh/uv/) | 執行設定指令、開發時跑後端 |
| Android Studio | 模擬器、建置 App。系統映像檔選有 **Google Play** 的版本，推播才收得到 |

Android SDK 第一次建置可能出現「License for package NDK … not accepted」，到 Android Studio → **SDK Manager** 同意授權，或執行 `sdkmanager --licenses`。

## 1. 第一次設定

```bash
uv run python -m scripts.init_env
```

會建立 `.env` 並產生加密金鑰（`.env` 不會被 commit）。預設值已經是模擬器用的設定，不用修改。

> ⚠️ `.env` 的 `FIELD_ENCRYPTION_KEY` 開始存資料後就不能更換，遺失就解不開已加密的電話、病史、過敏。換電腦 Demo 時要把 `.env` 一起帶過去。

## 2. 啟動（Demo 用）

```bash
docker compose --profile app up -d --build
```

會啟動資料庫和後端，後端每次啟動都會自動：

1. 更新資料表（`alembic upgrade head`）
2. 匯入範例資料：救護人員名冊、藥品資料、**聯醫之後 2 週的門診**（已有的資料與預約不會被覆蓋）
3. 啟動內建排程，每分鐘檢查吃藥提醒、沒回應通知、回診與預約提醒

確認：

- 電腦瀏覽器打開 <http://localhost:8000/health>，應顯示 `{"status":"ok"}`
- API 文件：<http://localhost:8000/docs>
- 看 log（推播內容、排程結果都在這裡）：`docker compose --profile app logs -f api`

停止：`docker compose --profile app stop`。資料存在 Docker volume，重新啟動後還在。

## 3. App 與前端的網址

| 給誰用 | 網址 |
|---|---|
| 模擬器裡的 App、前端呼叫後端 | `http://10.0.2.2:8000/api/v1` |
| 模擬器裡的服務網址（`my_service_model.dart` 的 `destinationUrl`） | `http://10.0.2.2:5173/` |
| 電腦瀏覽器開前端 | `http://localhost:5173`（已在 `EXTRA_CORS_ORIGINS` 允許） |

**App 已經設定好允許 http**：Android 9 以上預設只允許 https，所以在 `android/app/src/debug/` 加了 `network_security_config.xml`，**只在 debug 版**允許連 `10.0.2.2`、`localhost`。用 Android Studio 或 `fvm flutter run` 跑的就是 debug 版；release 版不受影響。

前端改用其他 port 時，同步修改 `.env` 的 `FRONTEND_BASE_URL` 與 `EXTRA_CORS_ORIGINS`，再重新啟動後端。

## 4. 兩台模擬器（長輩＋家人）

Android Studio 的 **Device Manager** 可以建立兩台模擬器同時開啟，一台登入長輩、一台登入家人，就能展示「女兒手機收到通知」。

兩台用不同的台北通帳號：修改 `assets/mock_data/account.json` 的 `id`、`realName`、`birthday` 後分別安裝到兩台模擬器。

## 5. 推播（Firebase 免費方案，選用）

不設定的話，推播內容會顯示在後端 log（`[push] … title=… body=…`），Demo 前可以先用 log 確認內容。

要讓模擬器真的收到通知：

1. 到 <https://console.firebase.google.com> 建立專案，維持免費的 **Spark** 方案（**不要升級**）。
2. **專案設定 → 服務帳戶 → 產生新的私密金鑰**，下載的 JSON 存成 `microservice/backend/secrets/firebase.json`（`secrets/` 不會被 commit、不會打包進映像檔）。
3. `.env` 設定 `FIREBASE_CREDENTIALS=secrets/firebase.json`，重新啟動後端。
4. App 端：在 Firebase 加入 Android App，取得 `google-services.json`，加上 `firebase_messaging` 與 `push_token` Handler（規格書 §2.1、§2.3）。

> 服務帳戶金鑰等同密碼，不要 commit、不要傳到群組。

---

## 開發時（後端改程式要即時生效）

用 Docker 只跑資料庫，後端用 uv 跑，存檔會自動重新載入：

```bash
docker compose up -d                       # 只啟動資料庫
uv run alembic upgrade head                # 更新資料表
uv run python -m seed.load                 # 匯入範例資料
uv run uvicorn app.main:app --reload       # 啟動後端（內建排程也會啟動）
```

不要同時開 Docker 的後端（`--profile app`），兩個都會佔用 port 8000。

## 常用操作

| 情況 | 指令 |
|---|---|
| 程式更新後重新啟動 | `docker compose --profile app up -d --build` |
| 立即執行一次排程 | `curl -X POST http://localhost:8000/api/v1/internal/tick -H "X-Internal-Secret: <.env 的 INTERNAL_SECRET>"` |
| 不等時間，立即觸發提醒（Demo） | 用 `/docs` 呼叫 `/api/v1/demo/trigger/*`（需要 `DEMO_MODE=true`） |
| **清空所有資料**重來 | `docker compose --profile app down -v`（會刪除資料庫，無法復原） |

## 疑難排解

| 狀況 | 檢查 |
|---|---|
| 模擬器打不開網頁、出現 `ERR_CLEARTEXT_NOT_PERMITTED` | 網址是否用 `10.0.2.2`；App 是否為 debug 版 |
| 模擬器連不到後端 | 電腦瀏覽器開 <http://localhost:8000/health> 是否正常；網址不要用 `localhost` |
| 前端呼叫被擋（CORS） | 前端網址是否和 `.env` 的 `FRONTEND_BASE_URL` 或 `EXTRA_CORS_ORIGINS` 完全相同 |
| port 5432 或 8000 被佔用 | 是否同時開了 uv 跑的後端、或電腦上另外裝了 PostgreSQL |
| 沒有收到提醒 | log 是否有 `[排程] 已啟動`；時段時間到了沒（或用 Demo 觸發）；推播內容是否出現在 log |
| 建置 App 出現 NDK 授權錯誤 | Android Studio → SDK Manager 同意授權 |

## Demo 前檢查清單

- [ ] `docker compose --profile app up -d --build`，log 有 `[排程] 已啟動`
- [ ] <http://localhost:8000/health> 正常
- [ ] `DEMO_MODE=true`
- [ ] 兩台模擬器都裝好 debug 版 App、登入不同帳號
- [ ] （有設定 Firebase 時）兩台模擬器都登記了推播
- [ ] 救護人員帳號 EMT-001（可登入）、EMT-003（無權限）
- [ ] 範例藥袋 QR（`seed/qr/`）放進模擬器的虛擬相機：模擬器 **Extended controls（⋯）→ Camera → Virtual scene**，把圖片設為牆面或桌面圖片，App 掃描時移動到圖片前即可
