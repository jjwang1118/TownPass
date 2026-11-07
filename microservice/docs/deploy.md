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
| Android Studio | 模擬器、建置 App。系統映像檔選有 **Google Play** 的版本，推播才收得到，也才有朗讀用的 Google 語音引擎 |

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
| 模擬器裡的服務網址（`my_service_model.dart` 的 `destinationUrl`） | `http://10.0.2.2:5173/`（電腦上要有網頁伺服器開在 port 5173，目前用法見 §6「測試朗讀」） |
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

## 6. 朗讀（念給我聽、吃藥提醒）

朗讀用**手機內建的離線語音**：網頁呼叫 App 的 `tts_speak`，App 用 `flutter_tts` 念出來（Android WebView 不支援網頁朗讀，一定要經過 App）。說明見 `microservice/frontend/tts/README.md`。

### 每台模擬器（或手機）都要做一次

1. 模擬器的系統映像檔選有 **Google Play** 的版本（才有 Google 語音引擎）。
2. 模擬器裡到 **設定 → 系統 → 語言 → 文字轉語音輸出**：
   - 偏好的引擎選 **Google 語音服務**
   - 按引擎旁的 ⚙ → **安裝語音資料** → 下載 **中文（台灣）**
   - 回上一頁按「播放」，聽得到中文才算完成
3. 實體 Android 手機一樣；Samsung 等手機預設是廠商自己的引擎，App 會在有 Google 語音引擎時優先使用。iOS 不用設定（需要 Mac 建置）。

> App **只使用離線語音**（比賽規定推論要在裝置端），沒下載中文語音資料時會顯示「找不到離線的中文語音」，不會改用網路。

### 拉下新程式後，App 一定要「完整重新安裝」

只要 `pubspec.yaml`、`AndroidManifest.xml` 或 `lib/util/web_message_handler/` 有改動，**hot reload／hot restart 都不會生效**，要重新建置並安裝。以下指令在**專案根目錄**（`TownPass/`）執行：

```bash
git branch --show-current          # 確認是有朗讀功能的分支（pubspec.yaml 裡有 flutter_tts）
fvm flutter pub get
fvm flutter run -d emulator-5554   # 或 Android Studio 先按 ■ 停止，再按 ▶ 執行
```

或先建置再手動安裝（不需要 Android Studio）：

```bash
fvm flutter build apk --debug
adb install -r build/app/outputs/flutter-apk/app-debug.apk
```

安裝後**直接點模擬器主畫面的 Town Pass 圖示**開啟。確認裝的是新版：

```bash
adb shell dumpsys package com.example.townpass | findstr lastUpdateTime   # Mac 用 grep
```

> ⚠️ 模擬器顯示的是 **UTC 時間**，台灣時間要加 8 小時。時間沒更新代表沒裝到新版：常見原因是用了 hot reload、建置失敗但模擬器還留著舊版，或 Android Studio 開的是別的資料夾或分支。

### 測試朗讀

前端還沒接上時，可以用朗讀測試頁：

1. **另外開一個終端機**，在 `microservice/frontend` 執行 `python -m http.server 5173`，**測試期間不要關**。電腦瀏覽器打開 <http://localhost:5173/tts/> 看得到測試頁才算成功。
2. **暫時**把 `lib/page/city_service/model/my_service_model.dart` 中「呷藥囉」的 `destinationUrl` 改成 `http://10.0.2.2:5173/tts/`，重新安裝 App（**這個改動不要 commit**）。
3. 開「服務 → 呷藥囉」，按「念給我聽」，應顯示「中文完成（使用：App 內建 TTS）」；再按「Read in English」確認英文也能念。第一次按可能要等 1–2 秒（引擎初始化）。英文顯示「找不到這個語言的離線語音」時，到語音資料下載**英文（美國）**。
4. 開**飛航模式**再按一次，確認離線也能念。

看 App 端每一步的紀錄：Android Studio 的 Logcat 搜尋 `[tts]`，或執行 `adb logcat | findstr "[tts]"`（Mac 用 `grep`）。

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
| App 裡打開「呷藥囉」是空白或顯示無法連線 | port 5173 的網頁伺服器有沒有開；電腦瀏覽器開 <http://localhost:5173/tts/> 是否正常；網址要用 `10.0.2.2` |
| 啟動網頁伺服器時顯示 port 5173 已被使用 | 是否已經開了另一個伺服器（例如前端的開發伺服器），同一時間只能開一個 |
| 朗讀顯示「App 沒有回應」 | App 是舊版：完整重新安裝並確認 `lastUpdateTime` 有更新（見 §6）；Logcat 按下時沒有 `[tts]` 紀錄也是同一個原因 |
| 朗讀顯示「找不到離線的中文語音」 | 模擬器沒下載中文（台灣）語音資料（見 §6） |
| 環境檢查顯示「speechSynthesis 不支援」「語音數量 0」 | Android WebView 本來就不支援，正常；朗讀靠 App |
| 朗讀顯示「語音引擎初始化逾時」 | 模擬器的語音引擎異常：到系統設定試聽一次，或重新開機模擬器；把 Logcat 的 `[tts]` 紀錄給負責的人看 |

## Demo 前檢查清單

- [ ] `docker compose --profile app up -d --build`，log 有 `[排程] 已啟動`
- [ ] <http://localhost:8000/health> 正常
- [ ] 前端網頁已開在 port 5173，電腦瀏覽器開得到（前端完成前用 §6 的 `python -m http.server 5173`）
- [ ] `DEMO_MODE=true`
- [ ] 兩台模擬器都裝好 debug 版 App、登入不同帳號
- [ ] 拉下最新程式後 App 有**完整重新安裝**（`lastUpdateTime` 已更新）
- [ ] 模擬器已下載**中文（台灣）語音資料**，開飛航模式按「念給我聽」聽得到
- [ ] （有設定 Firebase 時）兩台模擬器都登記了推播
- [ ] 救護人員帳號 EMT-001（可登入）、EMT-003（無權限）
- [ ] 範例藥袋 QR（`seed/qr/`）放進模擬器的虛擬相機：模擬器 **Extended controls（⋯）→ Camera → Virtual scene**，把圖片設為牆面或桌面圖片，App 掃描時移動到圖片前即可
