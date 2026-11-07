# 呷藥囉｜後端部署步驟（全部使用免費方案）

比賽規定不能使用付費服務，所以全部選**不用綁信用卡的永久免費方案**。

| 元件 | 服務 | 免費方案限制 |
|---|---|---|
| 後端 API | Render Web Service（Free） | 512 MB 記憶體；閒置 15 分鐘休眠；每月 750 小時 |
| 資料庫 | Neon（Free） | 0.5～1 GB，比賽用量足夠 |
| 每分鐘排程 | cron-job.org | 完全免費 |
| 推播 | Firebase Spark（免費方案）的 Cloud Messaging | 免費 |

cron-job.org 每分鐘呼叫一次後端，Render 就不會休眠；一個月約 720 小時，在 750 小時內。

> ⚠️ **不要使用**：Render 的 Postgres（免費 30 天後過期）、Render 的 Cron Jobs（沒有免費方案）、任何要求綁定信用卡或「升級」的功能。

> 指令都在 `microservice/backend` 目錄執行，Windows（PowerShell）、Mac 都一樣。

---

## 1. 建立資料庫（Neon）

1. 到 <https://neon.tech> 用 GitHub 或 Google 帳號註冊（不用信用卡），建立專案，Region 選 **AWS Asia Pacific (Singapore)**。
2. 在專案首頁按 **Connect**，**關閉「Connection pooling」**，複製連線字串，格式類似：
   `postgresql://USER:PASSWORD@ep-xxx.ap-southeast-1.aws.neon.tech/neondb?sslmode=require`
3. 直接貼上即可，後端會自動轉成需要的格式。

## 2. 產生部署用的環境變數檔

```bash
uv run python -m scripts.gen_secrets
```

會產生 `.env.cloud`，裡面已經有 3 組新金鑰（不會印在畫面上）。打開它填寫：

| 變數 | 填什麼 |
|---|---|
| `DATABASE_URL` | 步驟 1 的 Neon 連線字串 |
| `FRONTEND_BASE_URL` | 前端的 Firebase Hosting 網址，例如 `https://xxx.web.app`（結尾不加 `/`）。前端還沒部署就先填預計的網址，之後再改 |
| `EXTRA_CORS_ORIGINS` | 預設 `http://localhost:5173`，讓前端在本機開發時也能連；不需要就清空 |
| `FIREBASE_CREDENTIALS` | 先留空（步驟 6 再填），推播內容會寫在 log |

`.env.cloud` 不會被 commit、不會打包進映像檔。

> ⚠️ **`FIELD_ENCRYPTION_KEY` 開始存資料後就不能更換**，遺失就解不開已加密的電話、病史、過敏。請另外存到密碼管理工具。

## 3. 建立資料表與匯入範例資料

```bash
uv run --env-file .env.cloud alembic upgrade head
uv run --env-file .env.cloud python -m seed.load
```

最後應該看到「聯醫門診（模擬）：新增 504 個門診」。

> 門診只會產生「匯入隔天起 2 週」，**Demo 前一天要再執行一次第二行**。

## 4. 部署到 Render

先確認程式碼已經 push 到 GitHub（Render 從 GitHub 抓程式碼建置）。

1. Render 首頁按 **New → Web Service**。
2. **Source Code**：連結 GitHub，選 `jjwang1118/TownPass`。
3. 依下表填寫：

   | 欄位 | 值 |
   |---|---|
   | Name | `chiah-ioh-lo-api`（會成為網址的一部分） |
   | Language | **Docker** |
   | Branch | `feature/backend-family`（合併到 main 後改成 `main`） |
   | Region | **Singapore**（和 Neon 同一區，速度最快） |
   | Root Directory | `microservice/backend` |
   | Instance Type | **Free** |

4. **Environment Variables**：按 **Add from .env**，把 `.env.cloud` 的內容整份貼上。
5. 展開 **Advanced**：
   - **Health Check Path**：`/health`
   - **Dockerfile Path** 確認指向 `microservice/backend/Dockerfile`（設定 Root Directory 後通常是 `./Dockerfile`）
   - **Auto-Deploy**：On Commit（push 後自動重新部署）
6. 按 **Deploy Web Service**。第一次建置約 5～10 分鐘。
7. 完成後頁面上方會顯示網址，類似 `https://chiah-ioh-lo-api.onrender.com`，以下用 `API_URL` 表示。

確認：打開 `API_URL/health`，應顯示 `{"status":"ok"}`；API 文件在 `API_URL/docs`。

> 如果 Logs 出現「部署設定有誤：…」，代表環境變數還有開發用的值或空白，照訊息到 **Environment** 修改後按 **Manual Deploy**。

## 5. 設定每分鐘排程（cron-job.org）

負責吃藥提醒、沒回應通知、回診提醒、預約提醒，同時讓 Render 不休眠。

1. 到 <https://cron-job.org> 註冊（免費）。
2. **Create cronjob**：

   | 欄位 | 值 |
   |---|---|
   | Title | `chiah-ioh-lo tick` |
   | URL | `API_URL/api/v1/internal/tick` |
   | Execution schedule | Every **1** minute |

3. 切到 **Advanced**：
   - **Request method**：`POST`
   - **Headers**：新增一個，Key `X-Internal-Secret`，Value 為 `.env.cloud` 裡的 `INTERNAL_SECRET`
   - **Time zone**：`Asia/Taipei`
4. 儲存後按 **Test run**，回應應為 200，內容類似 `{"created":0,"repushed":0,…}`。

## 6. 推播（Firebase，免費方案）

1. 到 <https://console.firebase.google.com> 建立專案（維持免費的 Spark 方案，**不要升級**）。前端的 Firebase Hosting 可以用同一個專案。
2. **專案設定 → 服務帳戶 → 產生新的私密金鑰**，下載 JSON 檔。
3. 二選一：
   - Render 的 **Environment → Secret Files** 新增檔案 `firebase.json`，內容貼上 JSON；`FIREBASE_CREDENTIALS` 設為 `/etc/secrets/firebase.json`
   - 或把 JSON 內容整段貼進 `FIREBASE_CREDENTIALS`
4. 存檔後 Render 會重新部署。

> 這個 JSON 等同密碼，不要 commit、不要傳到群組。

App 端還需要：在 Firebase 加入 Android、iOS App，取得 `google-services.json`、`GoogleService-Info.plist`，加上 `firebase_messaging` 與 `push_token` Handler（規格書 §2.1、§2.3）。

## 7. 交給前端

- API 網址：`API_URL/api/v1`
- 前端網址必須和 `FRONTEND_BASE_URL`（或 `EXTRA_CORS_ORIGINS`）完全相同，否則瀏覽器會擋下請求（CORS）。

---

## 之後更新

| 情況 | 要做的事 |
|---|---|
| 只改程式 | push 到 GitHub，Render 會自動重新部署 |
| 改了 `models.py`（有新的 migration） | **先**執行步驟 3 的 `alembic upgrade head`，**再** push |
| 改環境變數 | Render → Environment 修改，存檔後自動重新部署（`.env.cloud` 也要同步改） |
| Demo 前一天 | 執行步驟 3 的 `seed.load`，產生之後 2 週的門診 |

## 疑難排解

| 狀況 | 檢查 |
|---|---|
| 看 log | Render 服務頁面 → **Logs** |
| 啟動失敗「部署設定有誤」 | 照訊息修改 Environment |
| 連不到資料庫 | Neon 連線字串是否為直接連線（主機名稱沒有 `-pooler`）、密碼是否正確 |
| 第一次打開很慢 | 免費方案休眠後喚醒約需 30～60 秒；cron-job.org 有在跑就不會休眠 |
| 前端呼叫被擋（CORS） | 前端網址是否和 `FRONTEND_BASE_URL` 完全相同（http/https、結尾 `/`） |
| 排程沒有執行 | cron-job.org 的執行紀錄；header 的 `INTERNAL_SECRET` 是否和 Render 上的相同 |
| 推播沒收到 | `FIREBASE_CREDENTIALS` 是否設定、App 是否已登記 `push_token` |
| 本月服務被暫停 | 750 小時用完了（例如同時開了兩個 Free 服務）；只保留一個 |

## Demo 前檢查清單

- [ ] 前一天執行 `seed.load`（門診）
- [ ] `DEMO_MODE=true`
- [ ] `API_URL/health` 正常
- [ ] cron-job.org 執行紀錄每分鐘都是 200
- [ ] 長輩、家人手機都登記了推播
- [ ] 救護人員帳號 EMT-001（可登入）、EMT-003（無權限）
