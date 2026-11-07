# 呷藥囉｜後端開發規格書

> 版本：v0.2（2026-11-08）
> 範圍：後端 API（Python FastAPI）。前端架構不在本文件範圍，只列出前端與 App 需要配合的事項。
> 依據：功能規格（文字版）、交付規格（圖檔版）與 UI 設計稿（`resent_docs/ui/`）。矛盾處的決議見 [§1.2](#12-規格決議)。

---

## 1. 總覽

### 1.1 產品範圍

呷藥囉在台北通內分成三區：

| 區 | 功能 | 本期 |
|---|---|---|
| 藥 | 藥單（拍照辨識、掃藥袋 QR、手動新增）、今天四個時段、吃藥提醒（長輩與家屬同時收到）、家人綁定 | ✅ |
| 救命卡（緊急醫療卡） | 長輩醫療資訊、隨機卡號、救護人員查看、查看紀錄與通知家人 | ✅ |
| 回診（Bonus） | 用藥天數算回診提醒、聯醫預約（看診時間與名額、前一天自動提醒；模擬資料） | ✅ |

### 1.2 規格決議

文字版、圖檔版與 UI 設計稿矛盾處，決議如下（2026-11-08 依 UI 設計稿調整第 3、4、5、7、9～11 項）：

| # | 項目 | 決議 |
|---|---|---|
| 1 | 名稱 | **呷藥囉**（UI 設計稿的「藥報平安」不採用） |
| 2 | 救護人員查詢方式 | **隨機卡號**（`TPE-XXXX-XXXX`），**不用身分證字號**（UI R02 的身分證字號欄位由前端改為卡號） |
| 3 | 提醒時段 | **固定四個**：早上 09:00、中午 12:00、晚上 18:00、睡前 22:00，不能修改；飯前、飯後只是標示，見 [§5.3](#53-吃藥時段與規則) |
| 4 | 藥品標示 | **藥單字母＋序號**（A1、A2…）：一個藥袋一張藥單，長輩在實體藥袋寫上大大的字母 |
| 5 | 緊急聯絡人 | **1 位**，必填 |
| 6 | 家人權限 | **唯讀**；但每次綁定後有**一次**初始設定機會，見 [§3.2](#32-家人的初始設定) |
| 7 | 新增藥品方式 | **拍照辨識、掃藥袋 QR、手動輸入**三條路徑，都先產生藥單草稿，逐項核對後加入；帶入聯醫用藥列為下一期 |
| 8 | 藥師角色 | **不需要** |
| 9 | 吃藥提醒對象 | 時間到時，長輩與所有綁定家屬**同時**收到；不再提醒、不需要長輩回應 |
| 10 | 回診預約提醒 | 預約後**自動**在前一天 18:00 提醒長輩與家屬（不需要「加入提醒」） |
| 11 | 救護人員登入 | 所屬分隊（下拉選單）＋人員編號＋密碼 |

### 1.3 比賽規則對後端的限制

- **AI 推論在裝置端**：後端不呼叫任何雲端 AI API，也不跑模型。拍藥袋照片的辨識由 App 的裝置端模型完成，後端「辨識 API」只負責比對健保藥品資料、算出每個欄位的信心分數（[§8.3](#83-拍照辨識的輸入)）。語音（TTS、台語錄音拼接）由前端處理，後端只提供結構化資料與國語朗讀稿文字（由 `speech` 模組用模板產生；藥名有中文就只念中文，只有英文就照原文念，科別、用途、稱呼不唸英文字母）。
- **開源免費**：所有套件需為 MIT、BSD、Apache-2.0 等可納入 AGPL 的授權，見 [§9](#9-技術選型)。
- **可移轉、可維運**：附 Dockerfile，依 README 即可建置。

---

## 2. 系統架構

```
┌──────────────┐  flutterObject   ┌────────────────┐   HTTPS/JSON   ┌──────────────────┐
│ 城市通 App    │ ◀──────────────▶ │ 微服務網頁       │ ─────────────▶ │ 後端 API          │
│ (Flutter)    │                  │ (WebView)      │                │ FastAPI（本機）   │
└──────▲───────┘                  └────────────────┘                └───┬──────┬───────┘
       │ FCM 推播                                                       │      │
       └────────────────────────────────────────────────────────────────┘      │
                                                                               ▼
                                     ┌──────────────────┐            ┌──────────────────┐
                                     │ 後端內建排程     │──每分鐘───▶│ PostgreSQL        │
                                     │ TickService      │  檢查提醒  │ （本機 Docker）   │
                                     │                  │            └──────────────────┘
                                     └──────────────────┘
```

### 2.1 推播（需要 App 修改）

城市通內建的 `notify` 只能顯示**本機通知**（`flutter_local_notifications`），伺服器無法透過它通知其他人的手機。以下功能都需要伺服器推播：

- 吃藥提醒（時間到同時通知長輩與家屬）
- 救護人員查看救命卡 → 通知家人
- 回診提醒、預約提醒

**做法**：App 加入 `firebase_messaging`（BSD-3），並依入門指引「以自訂 Handler 擴充 App 能力」的四個步驟新增 `push_token` Handler（見 [§2.3](#23-與城市通-app-的溝通)），把 FCM token 交給網頁，網頁再呼叫 `POST /devices` 登記。後端用 `firebase-admin` 發送。

### 2.2 排程

本地部署由**後端內建排程**每分鐘執行一次 `TickService`，檢查到期的提醒（`app/modules/internal/scheduler.py`）。`POST /internal/tick` 保留給手動測試。詳見 [§6](#6-排程與推播)。

### 2.3 與城市通 App 的溝通

完全遵照《城市通入門指引》第 03 章與 App 原始碼 `lib/util/web_message_handler/`：

- 網頁送出：`window.flutterObject.postMessage(JSON.stringify({ name, data }))`
- App 回覆：同樣是 `{ name, data }` 的 JSON 字串，網頁以 `JSON.parse(event.data)` 取得
- 用完要 `removeEventListener`；一般瀏覽器沒有 `flutterObject`，要先判斷是否存在

後端不直接和 App 溝通，因此規定：

1. **App → 後端**：前端把 App 的回覆 `JSON.parse` 後，**原封不動**放進 request body，不自行改欄位名稱。後端 schema 逐欄對照 App 實際回傳的格式（`app/integrations/townpass/messages.py`）。
2. **後端 → App**：需要呼叫 App 的地方，後端在回應中附上完整的 `{ name, data }`，前端直接 `postMessage(JSON.stringify(...))`。

| name | 方向 | 使用的 API | data 格式（依 App 原始碼） |
|---|---|---|---|
| `userinfo` | App → 後端 | `POST /auth/townpass` | `lib/bean/account.dart` 的 `Account`（駝峰式，如 `realName`、`phoneNo`、`birthday: "YYYY/MM/DD"`）；沒有帳號時為 `[]`，後端回 400 |
| `qr_code_scan` | App → 後端 | `POST …/prescriptions/qr-preview`、`POST /responder/cards/lookup`、`POST /family/bindings` | 掃到的字串；使用者取消時為 `null` |
| 拍照辨識（自訂，名稱由 App 決定） | App → 後端 | `POST …/prescriptions/photo-preview` | 裝置端模型整理出的藥單欄位，格式見 [§8.3](#83-拍照辨識的輸入) |
| `location` | App → 後端 | `POST /responder/cards/lookup` | geolocator `Position.toJson()`（`latitude`、`longitude`、`timestamp`…）；失敗時為 `[]`，後端視為沒有定位 |
| `push_token`（自訂） | App → 後端 | `POST /devices` | `{ "token": "…", "platform": "ios" \| "android" }` |
| `phone_call` | 後端 → App | 緊急聯絡人的 `call` 欄位 | 電話號碼字串，只含數字與開頭的 `+`（App 會組成 `tel://{data}`） |
| `launch_map` | 後端 → App | 院區、預約的 `map` 欄位 | 地圖網址 |
| `notify` | 前端 → App | （後端不使用） | `{ title, content }`；**內容不可包含「已訂閱」「已取消訂閱」**，否則 App 會改動訂閱清單 |

自訂 Handler `push_token` 依指引：繼承 `TPWebMessageHandler`、`name` 不可和內建名稱重複、加入 `TPWebMessageListener._cachedMessageHandlers`、設定 `Info.plist` 與 `AndroidManifest` 權限。

`tests/test_townpass_messages.py` 會讀取 App 的 `assets/mock_data/account.json` 與 handler 原始碼，確認後端格式和 App 一致；App 改版時重跑即可發現差異。

---

## 3. 角色與權限

| 角色 | 登入方式 | 說明 |
|---|---|---|
| 長輩 `elder` | 台北通 userinfo | 管理自己的藥單、救命卡、家人綁定、預約 |
| 家人 `family` | 台北通 userinfo | 以邀請碼綁定長輩；唯讀（初始設定除外） |
| 救護人員 `responder` | 所屬分隊＋人員編號＋密碼（模擬 A12345 等 3 筆） | 只能查看救命卡；登入 12 小時有效 |
| 路人 | 不登入 | 掃 QR 只看到「請撥打 119」，不呼叫後端 |

身分在第一次使用時選擇（長輩或家人），存在 `users.role`。

### 3.1 權限矩陣

| 資源 | 長輩本人 | 已綁定家人 | 救護人員 |
|---|---|---|---|
| 藥單、藥品 | 讀寫 | 讀（初始設定時可寫） | — |
| 吃藥提醒 | 讀 | 讀；同時收到推播；可「提醒長輩吃藥」 | — |
| 救命卡、緊急聯絡人 | 讀寫 | 讀（初始設定時可寫） | 讀（需卡號） |
| 救命卡重新產生卡號 | 可 | 可（初始設定後也可以） | — |
| 撤回健康資料同意 | 可 | — | — |
| 救命卡查看紀錄 | 讀 | 讀 | — |
| 家人綁定 | 產生邀請碼、解除 | 使用邀請碼 | — |
| 預約回診 | 讀寫 | 讀 | — |

「重新產生卡號」開放給家人，因為卡片遺失時可能是家人發現。

### 3.2 家人的初始設定

- 每一筆綁定（`family_bindings`）都有一次初始設定機會。
- 綁定成功後，家人可以新增或修改：藥單、救命卡（含緊急聯絡人）、預約。
- 家人按下「完成設定」後，寫入 `family_bindings.setup_completed_at`，之後該家人對這位長輩全部唯讀。
- 後端在每個寫入 API 檢查：`role == elder 且是本人` 或 `是已綁定家人 且 setup_completed_at IS NULL`。
- 解除綁定後重新綁定，會產生新的綁定紀錄，因此有新的一次機會。重新綁定需要長輩產生邀請碼，所以由長輩控制。

---

## 4. 分層設計

### 4.1 三層架構

每個模組都用同樣的三層：

| 層 | 檔案 | 負責 | 不可以做 |
|---|---|---|---|
| API 層 | `router.py` | HTTP 路由、輸入驗證、權限檢查（`Depends`）、回應格式 | 直接存取資料庫；寫業務規則 |
| 業務層 | `service.py` | 業務規則、交易邊界、跨模組協調 | import `fastapi`；丟 `HTTPException` |
| 資料層 | `repository.py`、`integrations/` | 存取資料庫、呼叫外部系統 | 寫業務規則；自行 commit |

共用的資料定義（不算一層）：

- `schemas.py`：Pydantic 模型，API 的輸入與輸出。
- `models.py`：SQLAlchemy ORM 模型，資料表。

**為什麼是三層而不是四層**：四層會再分出獨立的 domain 層，讓業務規則完全不依賴資料庫，適合長期維護的大型系統。比賽時間短，決選有問答，全組用同一套三層結構比較好分工和說明。

**純計算放 `rules.py`**：時段分配、剩餘天數、回診日期、卡號產生等沒有 I/O 的計算，寫成純函式放在模組的 `rules.py`，由 service 呼叫。這不是另一層，只是方便寫單元測試。

### 4.2 規則

1. **呼叫方向只能往下**：router → service → repository／integration。
2. **跨模組只能 service 呼叫 service**。例如救命卡要讀「正在吃的藥」，呼叫 `MedicationService.list_active()`，不可以 import `medication/repository.py`。
3. **交易由 service 控制**：一個 API 請求一個交易，service 方法結束時 commit；repository 只 `flush`。
4. **錯誤**：service 丟 `core/errors.py` 定義的業務錯誤（如 `NotFound`、`Forbidden`、`Conflict`），由全域 exception handler 轉成 HTTP 狀態碼，格式見 [§7.1](#71-共通規則)。
5. **外部系統用介面**：`integrations/` 每個外部系統都有介面與模擬實作，由設定決定使用哪一個；service 不知道是不是模擬資料。

### 4.3 目錄結構

```
microservice/backend/
├── Dockerfile
├── pyproject.toml
├── alembic.ini
├── alembic/versions/            # 資料表變更
├── seed/                        # Demo 用資料（帳號、名冊、門診、範例 QR）
├── tests/
└── app/
    ├── main.py                  # 建立 FastAPI、掛載 router、exception handler
    ├── core/
    │   ├── config.py            # 環境變數（pydantic-settings）
    │   ├── db.py                # async engine、session
    │   ├── security.py          # JWT、密碼雜湊、欄位加密
    │   ├── deps.py              # 共用 Depends：目前使用者、權限
    │   ├── errors.py            # 業務錯誤與 handler
    │   └── clock.py             # 取得現在時間（測試可替換）
    ├── modules/
    │   ├── auth/                # 台北通登入、身分選擇
    │   ├── family/              # 邀請碼、綁定、初始設定
    │   ├── medication/          # 藥單、三條路徑（QR、拍照比對、手動）、同成分、藥名搜尋、今天四個時段
    │   ├── reminder/            # 吃藥提醒（長輩與家屬同時）、回診提醒
    │   ├── speech/              # 朗讀稿模板（國語、英文）
    │   ├── emergency_card/      # 救命卡、卡號、查看紀錄、同意
    │   ├── responder/           # 救護人員登入、名冊驗證
    │   ├── appointment/         # 院區、科別、醫師、門診、預約
    │   ├── notification/        # 裝置 token、FCM 發送
    │   └── internal/            # /internal/tick 排程入口
    │       # 每個模組內：router.py / service.py / repository.py
    │       #             schemas.py / models.py / rules.py（需要時）
    └── integrations/
        ├── townpass/            # 城市通 App 的 { name, data } 訊息格式（§2.3）
        ├── tpech/               # 北市聯醫：院區、門診（模擬）
        ├── fire_dept/           # 消防局人員名冊（模擬）
        ├── fda/                 # 藥品資料（匯入健保用藥品項）
        └── fcm/                 # Firebase Cloud Messaging
```

---

## 5. 資料庫設計

### 5.1 選擇

- **PostgreSQL**：資料關聯強（使用者、綁定、藥品、預約、紀錄），且需要交易（邀請碼只能用一次、門診名額）。
- **部署**：本地 Docker（`compose.yaml`），資料存在 volume `pgdata`。
- **工具**：SQLAlchemy 2.0（async）+ `asyncpg`，Alembic 管理資料表變更。
- **時間**：一律存 `timestamptz`（UTC），業務邏輯以 `Asia/Taipei` 計算。
- **主鍵**：`uuid`。

### 5.2 資料表

🔒 表示應用層加密欄位（見 [§5.4](#54-個資保護)）。

#### 使用者與綁定

**`users`**

| 欄位 | 型別 | 說明 |
|---|---|---|
| id | uuid PK | |
| townpass_id | text UNIQUE | 台北通 userinfo `id` |
| role | enum `elder` / `family` | 第一次使用時選擇 |
| real_name | text | userinfo `realName` |
| phone | text 🔒 | userinfo `phoneNo`，家人「一鍵撥號」用 |
| birth_year | int | 由 userinfo `birthday` 取年份 |
| created_at | timestamptz | |

不儲存身分證字號（userinfo 的 `idNo`），本服務用不到。

**`family_invites`**

| 欄位 | 型別 | 說明 |
|---|---|---|
| id | uuid PK | |
| elder_id | uuid FK users | |
| code | char(6) | 6 位數字 |
| expires_at | timestamptz | 建立後 10 分鐘 |
| used_at | timestamptz NULL | 使用後失效 |
| used_by | uuid FK users NULL | |

產生時檢查「未使用且未過期」的邀請碼中沒有重複。使用時以 `UPDATE … WHERE used_at IS NULL AND expires_at > now()` 確保只能用一次。

**`family_bindings`**

| 欄位 | 型別 | 說明 |
|---|---|---|
| id | uuid PK | |
| elder_id | uuid FK users | |
| family_id | uuid FK users | |
| relation_label | text | 家人對長輩的稱呼，如「媽媽」，用於通知文字 |
| notify_on_ack | bool default true | 目前未使用（吃藥提醒已改為不需回應） |
| setup_completed_at | timestamptz NULL | NULL 表示還能做初始設定 |
| created_at | timestamptz | |
| revoked_at | timestamptz NULL | 解除綁定 |

唯一索引：`(elder_id, family_id) WHERE revoked_at IS NULL`。

#### 藥

**`prescriptions`**：藥單，一個藥袋一張。

| 欄位 | 型別 | 說明 |
|---|---|---|
| id | uuid PK | |
| elder_id | uuid FK users | |
| letter | char(1) | 藥單字母 A～Z；吃藥中的藥單不重複，吃完後釋放 |
| source | enum `photo` / `qr` / `manual` | 拍照辨識、掃 QR、手動 |
| hospital / department / doctor | text NULL | 院區、科別、醫師；手動新增時可之後補填 |
| visit_date | date | 看診日，從這天開始吃 |
| days | int | 給藥天數（必填） |
| status | enum `active` / `finished` | 吃藥中、已吃完 |
| finished_at | timestamptz NULL | |
| created_by | uuid FK users | 核對並加入的人（長輩或做初始設定的家人） |
| created_at / updated_at | timestamptz | |

唯一索引：`(elder_id, letter) WHERE status = 'active'`。過了吃藥天數的藥單在查詢或新增時自動改為 `finished`。

**`medications`**：藥單裡的藥。

| 欄位 | 型別 | 說明 |
|---|---|---|
| id | uuid PK | |
| prescription_id | uuid FK prescriptions | |
| elder_id | uuid FK users | |
| seq | int | 藥單內的序號；編號 = 字母＋序號（A1） |
| name | text | 藥名（藥袋上的寫法） |
| license_no | text NULL | 健保藥品代號，用於同成分檢查 |
| strength | text NULL | 劑量，例如「5 毫克」 |
| purpose | text NULL | 用途 |
| dose_qty | numeric(3,1) | 一次幾顆，支援半顆 |
| slots | text[] | 什麼時候吃：`morning` / `noon` / `evening` / `bedtime`，可複選 |
| meal_timing | enum `before` / `after` | 飯前、飯後 |
| needs_review | bool | 待核對（劑量選了「看不清楚／不確定」） |
| status | enum `active` / `stopped` | |
| stopped_at | timestamptz NULL | |
| stop_reason | enum `finished` / `doctor_advised` NULL | 停用原因：吃完了、醫生說不用吃了 |
| created_at / updated_at | timestamptz | |

唯一索引：`(prescription_id, seq)`。

**`drug_licenses`**：從健保署「健保用藥品項查詢檔」匯入（約 4.5 萬筆），只讀。

| 欄位 | 型別 | 說明 |
|---|---|---|
| license_no | text PK | 健保藥品代號（10 碼） |
| name_zh / name_en | text | 中、英文品名 |
| ingredients | text[] | ATC 代碼，只有 7 碼（同一種化學成分）時才放；3～5 碼的藥物類別不放 |
| product_en / product_zh | text | 產品名（去掉劑量、藥廠、括號），藥名搜尋「同藥名只出現一次」用 |
| ingredient_en | text | 英文品名括號內的主成分 |
| strength | text | 劑量，例如「5 毫克」 |
| form | text | 劑型，例如「錠劑」 |

#### 提醒

**`reminder_events`**：每位長輩、每個時段、每天最多一筆。

| 欄位 | 型別 | 說明 |
|---|---|---|
| id | uuid PK | |
| elder_id | uuid FK users | |
| slot_key | enum `morning` / `noon` / `evening` / `bedtime` | |
| scheduled_date | date | 台北日期 |
| scheduled_at | timestamptz | 該次提醒時間 |
| groups | jsonb | 快照：依藥單分組的藥（字母、院區、科別、每個藥的編號與顆數） |
| pushed_at | timestamptz | 推播長輩與家屬的時間 |

唯一索引：`(elder_id, slot_key, scheduled_date)`，避免排程重複建立。

**`refill_notices`**：回診提醒的發送紀錄，`(elder_id, run_out_date)` 為主鍵，`letters` 記錄提醒了哪幾張藥單，同一個吃完日只發一次。

#### 救命卡

**`emergency_cards`**：每位長輩一張。

| 欄位 | 型別 | 說明 |
|---|---|---|
| id | uuid PK | |
| elder_id | uuid FK users UNIQUE | |
| name | text 🔒 | 姓名；推播給家屬時也用 |
| birth_date | date | 出生年月日（顯示年齡） |
| gender | enum | |
| blood_type | enum `A` / `B` / `O` / `AB` / `unknown` | 血型 |
| chronic_conditions | text 🔒 | JSON 陣列，加密後儲存 |
| allergies | text 🔒 | JSON 陣列：`[{"type":"drug","name":"盤尼西林"},{"type":"food","name":"海鮮"}]` |
| updated_at / updated_by | | |

不收集常去醫院與病歷號（UI E14）。

「正在吃的藥」不存在這張表，查詢時由 `MedicationService` 即時帶入。

**`emergency_contacts`**：每張卡 1 筆，和救命卡一起儲存。

| 欄位 | 型別 | 說明 |
|---|---|---|
| id | uuid PK | |
| card_id | uuid FK | |
| name | text 🔒 | |
| relation | text | |
| phone | text 🔒 | |
| sort_order | int | |

**`card_codes`**：卡號紀錄，重新產生後舊卡號立即失效。

| 欄位 | 型別 | 說明 |
|---|---|---|
| code | text PK | `TPE-XXXX-XXXX` |
| card_id | uuid FK | |
| created_at | timestamptz | |
| revoked_at | timestamptz NULL | NULL 表示目前有效 |

唯一索引：`(card_id) WHERE revoked_at IS NULL`，每張卡只有一組有效卡號。

**`card_access_logs`**：只能新增，不提供修改或刪除 API。

| 欄位 | 型別 | 說明 |
|---|---|---|
| id | uuid PK | |
| card_id | uuid FK | |
| responder_id | uuid FK responders | |
| responder_name / responder_unit / responder_staff_no | text | 查看當下的姓名、分隊、人員編號（快照，之後離職或調動也不變） |
| code_used | text | 使用的卡號 |
| method | enum `qr` / `manual` | 掃描或手動輸入 |
| latitude / longitude | numeric NULL | 救護人員手機定位 |
| accessed_at | timestamptz | |

**`consents`**

| 欄位 | 型別 | 說明 |
|---|---|---|
| id | uuid PK | |
| user_id | uuid FK users | 長輩 |
| type | enum `health_data` | |
| granted_at | timestamptz | |
| granted_by | uuid FK users | 本人或初始設定的家人 |
| revoked_at | timestamptz NULL | |

#### 救護人員

**`responders`**：模擬消防局名冊。

| 欄位 | 型別 | 說明 |
|---|---|---|
| id | uuid PK | |
| account | text UNIQUE | 人員編號，例如 `A12345` |
| password_hash | text | argon2 |
| name | text | |
| unit | text | 所屬分隊，如「中山分隊」 |
| unit_phone | text | 分隊電話，查看救命卡後讓家人一鍵撥號 |
| title | text | 職稱 |
| employment_status | enum `active` / `resigned` | |
| has_ems_permission | bool | 是否有救護權限 |

正式版名冊由消防局提供，透過 `integrations/fire_dept` 查詢；比賽時直接讀這張表。

#### 回診

| 資料表 | 主要欄位 | 說明 |
|---|---|---|
| `hospitals` | id、name、address | 聯醫 7 院區：中興、仁愛、和平婦幼（和平、婦幼 2 個院址）、忠孝、陽明、松德、林森中醫昆明（林森、昆明 2 個院址），共 9 筆，名稱與地址依聯醫官網 |
| `departments` | id、hospital_id、name | 科別 |
| `doctors` | id、department_id、name | 醫師 |
| `clinic_sessions` | id、doctor_id、date、period（`morning` / `afternoon` / `evening`）、issued_count（已發出的看診號碼）、status（`open` / `suspended`） | 門診（某位醫師某天的上午、下午或晚上） |
| `clinic_slots` | id、session_id、time（例如 09:30）、capacity、booked_count（有效預約數） | 看診時間，各自有名額；額滿時前端顯示灰色 |
| `appointments` | id、elder_id、session_id、slot_id、visit_no（看診號碼）、status（`booked` / `cancelled`）、cancelled_at、reminded_day_before_at、created_at | 同一位長輩同一個門診只能有一筆有效預約 |

預約時以 `UPDATE clinic_slots SET booked_count = booked_count + 1 WHERE id = ? AND booked_count < capacity AND 門診開放且在明天起 14 天內 RETURNING session_id` 確保不超額，再以 `UPDATE clinic_sessions SET issued_count = issued_count + 1 RETURNING issued_count` 發看診號碼。取消時只減 `booked_count`，所以名額釋出、看診號碼不會重複發給別人。

#### 推播

**`device_tokens`**：user_id、token（UNIQUE）、platform、updated_at。一個使用者可以有多台裝置。

### 5.3 吃藥時段與規則

**固定四個時段**（不能修改，`medication/rules.py`）：

| slot_key | 名稱 | 時間 |
|---|---|---|
| `morning` | 早上 | 09:00 |
| `noon` | 中午 | 12:00 |
| `evening` | 晚上 | 18:00 |
| `bedtime` | 睡前 | 22:00 |

每個藥自己記錄「什麼時候吃」（可複選），飯前、飯後只是標示，不影響提醒時間。藥袋 QR 或拍照辨識給的是頻率時，換成時段：

| 頻率 | 時段 |
|---|---|
| `QD` 一天一次 | 早上 |
| `BID` 一天兩次 | 早上、晚上 |
| `TID` 一天三次 | 早上、中午、晚上 |
| `QID` 一天四次 | 早上、中午、晚上、睡前 |
| `HS` 睡前 | 睡前 |

**其他計算規則**：

- **剩餘天數** = `visit_date + days − 今天`，小於 0 顯示 0。
- **藥吃完日** = `visit_date + days − 1`。
- **藥單字母** = 該長輩吃藥中的藥單沒用到的第一個字母（A～Z）。吃完或提早移到「已吃完」後字母釋放。
- **藥的編號** = 字母＋藥單內的序號（A1、A2…）。

### 5.4 個資保護

- 慢性病、過敏、用藥屬個資法第 6 條特種個資。救命卡寫入前必須有有效的 `consents`（`health_data`），否則回 `403 CONSENT_REQUIRED`。
- **撤回同意**：只有長輩本人可以撤回。清空 `chronic_conditions`、`allergies`，並撤銷有效卡號；查看紀錄、姓名、緊急聯絡人保留。重新同意並儲存後補發新卡號。
- **欄位加密**：🔒 欄位用 `cryptography` 的 Fernet（AES-128-CBC + HMAC）在應用層加密，金鑰放環境變數 `FIELD_ENCRYPTION_KEY`（正式版放 Secret Manager）。
- **查看紀錄**只能新增。
- 救護人員查詢回應附上免責文字：「本資料由本人或家屬提供，僅供參考，請以醫療專業判斷為準」。
- 電子同意的形式需請法律專業確認（交付規格第 9 點）。

---

## 6. 排程與推播

### 6.1 `/internal/tick`

後端內建排程每分鐘執行一次（也可手動呼叫，header 帶 `X-Internal-Secret`）。每次執行以下工作，每項都要可以重複執行而不重複發送：

| 工作 | 條件 | 動作 |
|---|---|---|
| 吃藥提醒 | 某長輩某時段（09:00、12:00、18:00、22:00）時間已到（延誤 30 分鐘內），該時段有藥、今天還沒建立 | 建 `reminder_events`，**同時**推播長輩與所有綁定家屬 |
| 回診提醒 | 每天 09:00 起；有藥單的吃完日 = 今天 + 7，且尚未發過（`refill_notices`） | 推播長輩與家人：「藥單 A（仁愛院區 心臟內科）再 7 天就吃完囉，要記得回診或領慢箋」 |
| 預約提醒 | 每筆有效預約，前一天 18:00 起一次 | 推播長輩與家屬（文字不同），`data.map` 為「帶我去醫院」的 `launch_map` 訊息 |

「建立」和「領取要提醒的預約」都用一條 SQL（`INSERT … ON CONFLICT DO NOTHING RETURNING`、`UPDATE … RETURNING`）完成，排程同時被呼叫兩次也只有一次會發出推播。

### 6.2 推播內容

推播一律帶 `data` 欄位，讓 App 點開後導到對應頁面：

```json
{
  "type": "medication_reminder",
  "event_id": "…",
  "deeplink": "https://<前端網址>/reminder/<event_id>"
}
```

| type | 對象 | 標題｜內文範例 |
|---|---|---|
| `medication_reminder` | 長輩 | 中午 12:00 該吃藥了｜B1、B2 各 1 顆，點開可以聽語音（UI E09） |
| `family_medication_reminder` | 家屬（同時） | 王美玉 中午 12:00 該吃藥了｜B1、B2 各 1 顆，記得關心她（UI F04；姓名取自救命卡，沒有時用台北通姓名） |
| `medication_nudge` | 長輩 | 家人提醒｜陳小美提醒你吃藥喔（家人的台北通姓名） |
| `card_accessed` | 家屬 | 救護人員查看了王美玉的緊急醫療卡｜11/07 14:32｜臺北市政府消防局 大安分隊｜人員編號 A12345。長輩可能需要緊急協助，請盡快聯絡。（UI F07；`data.call` 為撥給長輩的 `phone_call` 訊息） |
| `refill_reminder` | 長輩、家屬 | 回診提醒｜藥單 A（仁愛院區 心臟內科）再 7 天就吃完囉，要記得回診或領慢箋 |
| `appointment_reminder` | 長輩 | 明天 09:30 要回診｜仁愛院區心臟內科林醫師，記得帶健保卡（UI E16） |
| `appointment_reminder` | 家屬 | 王美玉 明天 09:30 要回診｜仁愛院區心臟內科林醫師，記得提醒或陪伴她（UI F08） |

點開吃藥提醒後的時段用藥詳情（`GET /reminders/{id}`）依藥單分組，朗讀稿「中午 12 點，要吃新陳代謝科 1 號 1 顆、2 號 1 顆」不念英文字母。全螢幕提醒、聲音、震動、國台語朗讀由 App 與前端處理。

---

## 7. API

### 7.1 共通規則

- 前綴：`/api/v1`。
- 認證：`Authorization: Bearer <JWT>`。JWT 內含 `sub`、`kind`（`user` / `responder`）、`exp`。
  - 長輩、家人：有效 7 天。
  - 救護人員：有效 12 小時（一個勤務班）。每次請求都重新確認名冊狀態，離職立即失效。
- 錯誤格式：

```json
{ "error": { "code": "INVITE_EXPIRED", "message": "邀請碼已過期，請長輩重新產生" } }
```

| HTTP | 業務錯誤 |
|---|---|
| 400 | `ValidationError`（含 QR 格式錯誤） |
| 401 | 未登入或登入過期 |
| 403 | `Forbidden`、`CONSENT_REQUIRED`、`RESPONDER_NOT_AUTHORIZED` |
| 404 | `NotFound`（含卡號無效） |
| 409 | `Conflict`（邀請碼已使用、看診時間額滿、藥單字母用完） |
| 429 | 卡號查詢過於頻繁 |

### 7.2 端點

`{elder_id}` 可以是本人或已綁定的長輩，權限依 [§3.1](#31-權限矩陣) 檢查。

**auth**

| 方法 | 路徑 | 說明 |
|---|---|---|
| POST | `/auth/townpass` | body 為 App 的 `userinfo` 回覆；建立或更新使用者，回 JWT |
| PUT | `/me/role` | 第一次使用時選擇身分（之後不能改；`DEMO_MODE` 時可改） |
| GET | `/me` | 自己的資料與身分（綁定清單見 `GET /family/bindings`） |

**family**

| 方法 | 路徑 | 說明 |
|---|---|---|
| POST | `/family/invites` | 長輩產生邀請碼，回 `code`、`qr_url`（邀請 QR 的內容：`{前端網址}/invite/{code}`）、`expires_at`；舊的有效邀請碼立即失效 |
| POST | `/family/bindings` | body：`qr`（App 的 `qr_code_scan` 回覆）或 `code`（手動輸入）擇一，加上稱呼 `relation_label`；完成綁定 |
| GET | `/family/bindings` | 綁定清單 |
| PATCH | `/family/bindings/{id}` | 家人修改 `relation_label`（`notify_on_ack` 目前未使用） |
| POST | `/family/bindings/{id}/complete-setup` | 家人完成初始設定，之後唯讀 |
| DELETE | `/family/bindings/{id}` | 長輩解除綁定 |

**medication**

| 方法 | 路徑 | 說明 |
|---|---|---|
| GET | `/drugs/search?q=` | 藥名搜尋（手動新增）：2 個字以上，中英文、不分大小寫、比對字首；同藥名只出現一次，附可選劑量清單（每個劑量帶健保藥品代號）；北市聯醫常用藥（模擬）排前面，最多 8 筆 |
| POST | `/elders/{elder_id}/prescriptions/qr-preview` | 掃 QR：body 為 App 的 `qr_code_scan` 回覆 |
| POST | `/elders/{elder_id}/prescriptions/photo-preview` | 拍照辨識：body 為裝置端模型整理出的欄位（[§8.3](#83-拍照辨識的輸入)）；比對健保資料、回每個欄位的信心分數與 `uncertain`（紅框） |
| POST | `/elders/{elder_id}/prescriptions/preview` | 手動新增、或修改後「再看一次」：body 為藥單草稿 |
| POST | `/elders/{elder_id}/prescriptions` | 「確認無誤，加入藥單」：body 為核對後的草稿；配字母、記錄核對者；回藥單、同成分警示、四個時段各吃哪幾號、「請用筆在這個藥袋上寫一個大大的「A」」 |
| GET | `/elders/{elder_id}/prescriptions?status=active\|finished` | 我的藥單：吃藥中（依字母）、已吃完（新的在前）；含每個藥的「念給我聽」朗讀稿 |
| GET | `/elders/{elder_id}/prescriptions/{id}` | 藥單詳細 |
| PATCH | `/elders/{elder_id}/prescriptions/{id}` | 補填院區、科別、醫師，或修改看診日、天數 |
| POST | `/elders/{elder_id}/prescriptions/{id}/finish` | 提早移到「已吃完」，字母釋放 |
| GET | `/elders/{elder_id}/medications/{id}` | 藥品詳細 |
| PATCH | `/elders/{elder_id}/medications/{id}` | 修改藥名、劑量、顆數、時段、飯前飯後、待核對 |
| POST | `/elders/{elder_id}/medications/{id}/stop` | body `{"reason": "finished" \| "doctor_advised"}`；停用後不再提醒 |
| GET | `/elders/{elder_id}/today?date=` | 今天四個時段的藥（首頁、時段用藥詳情、家屬首頁）：依藥單分組，附朗讀稿；沒有藥的時段不列出 |
| GET | `/elders/{elder_id}/next-dose` | 首頁「下一次吃藥」 |

三個預覽 API 都回同一個格式：預計配的字母、草稿 `draft`、每個藥的編號與時段、同成分警示、`uncertain`、四個時段各吃哪幾號。預覽不寫入。

**reminder**

| 方法 | 路徑 | 說明 |
|---|---|---|
| GET | `/reminders/{event_id}` | 點開推播：時段、依藥單分組的藥、朗讀稿 `speech_text`（國語）與 `speech_text_en`（英文） |
| GET | `/elders/{elder_id}/reminders?date=` | 某天的提醒 |
| POST | `/elders/{elder_id}/nudge` | 綁定的家人提醒長輩吃藥 |

**emergency_card**

| 方法 | 路徑 | 說明 |
|---|---|---|
| POST | `/elders/{elder_id}/consents` | 同意儲存健康資料；已同意時回傳原紀錄 |
| DELETE | `/elders/{elder_id}/consents/health_data` | 撤回同意（只有長輩本人） |
| GET | `/elders/{elder_id}/emergency-card` | 長輩、家人檢視（姓名、年齡、性別、血型、一位緊急聯絡人、慢性病、過敏、來自藥單的目前用藥、卡號與 QR 內容、查看紀錄）；還沒建立時回 `404 CARD_NOT_CREATED` |
| PUT | `/elders/{elder_id}/emergency-card` | 儲存整張卡：姓名、出生年月日、一位緊急聯絡人必填；聯絡人回應附 `phone_call` 訊息 |
| POST | `/elders/{elder_id}/emergency-card/regenerate-code` | 重新產生卡號，舊卡號立即失效 |
| GET | `/emergency-card/common-items` | 常見慢性病、過敏選項 |

**responder**

| 方法 | 路徑 | 說明 |
|---|---|---|
| GET | `/responder/units` | 所屬單位下拉選單（臺北市政府消防局各分隊，名稱為範例）；不需登入 |
| POST | `/responder/login` | body `{unit, staff_no, password}`，比對名冊；單位、編號或密碼錯誤都回 `401 INVALID_CREDENTIALS`（不透露帳號是否存在），離職或無救護權限回 `403 RESPONDER_NOT_AUTHORIZED`「無權限」 |
| POST | `/responder/cards/lookup` | body：`qr`（App 的 `qr_code_scan` 回覆）或 `code`（手動輸入）擇一，加上 `location`（App 的 `location` 回覆）；回救命卡內容；寫查看紀錄並推播家人 |

查詢回應只有必要欄位（UI R03）：姓名、年齡、性別、血型、一位緊急聯絡人（撥號）、慢性病、過敏、目前用藥，不含常去醫院與病歷號；並附免責文字與 `close_at`（查詢後 30 分鐘，前端到時自動關閉並清除畫面資料）。每位救護人員每分鐘最多查詢 10 次（超過回 `429 RATE_LIMITED`），避免猜卡號；次數記在後端記憶體，重新啟動後歸零。

**appointment**

| 方法 | 路徑 | 說明 |
|---|---|---|
| GET | `/hospitals` | 選院區：9 個院址附地址與 `launch_map` 訊息（帶我去醫院） |
| GET | `/hospitals/{id}/departments?elder_id=` | 選科別；帶 `elder_id` 時，最近藥單的科別排第一並附 `from_letter`（「已從藥單 A 帶入科別」） |
| GET | `/departments/{id}/doctors?elder_id=` | 選醫師：每週門診時間（「週一、週五 上午」）；2 週內都額滿時 `available=false`、`note=已額滿`；藥單上的醫師排第一並標記 |
| GET | `/doctors/{id}/sessions` | 選日期：明天起 2 週的門診（「11/14（五）」「上午門診」）；額滿、停診不可選 |
| GET | `/sessions/{id}/slots` | 選時段：每個看診時間（「上午 09:30」）的剩餘名額（「還有 3 個名額」「已額滿」） |
| POST | `/elders/{elder_id}/appointments` | 確認預約：body `{"slot_id"}`；回預約成功頁（看診號碼、日期、時段、院區、科別、醫師、帶我去醫院） |
| GET | `/elders/{elder_id}/appointments` | 我的預約：今天以後、未取消，依日期與時間排序 |
| POST | `/elders/{elder_id}/appointments/{id}/cancel` | 取消；看診日已過不能取消 |

**notification、internal**

| 方法 | 路徑 | 說明 |
|---|---|---|
| POST | `/devices` | body 為 App 的 `push_token` 回覆；登記 FCM token |
| DELETE | `/devices/{token}` | 移除 token |
| POST | `/internal/tick` | 排程入口，見 [§6.1](#61-internaltick) |

---

## 8. 格式定義

### 8.1 藥袋 QR

比賽時自行產生範例 QR。**一個藥袋（一張藥單）一個 QR**，內容為 JSON：

```json
{
  "v": 2,
  "t": "rx",
  "hosp": "臺北市立聯合醫院仁愛院區",
  "dept": "心臟內科",
  "dr": "王醫師",
  "date": "2026-11-05",
  "days": 28,
  "items": [
    {"lic": "B021571100", "name": "Amlodipine", "mg": "5 毫克", "use": "降血壓", "qty": 1, "when": ["morning"], "meal": "after"},
    {"lic": "B022890100", "name": "Atorvastatin", "mg": "20 毫克", "use": "降血脂", "qty": 1, "freq": "HS", "meal": "after"}
  ]
}
```

- `v`：格式版本。仍接受 v1（一個 QR 一個藥）；其他版本、不是藥袋 QR 或缺欄位回 `400 QR_INVALID`。
- `lic`：健保藥品代號（10 碼）；`mg`：劑量。
- `when`（時段，可複選）與 `freq`（頻率，換算見 [§5.3](#53-吃藥時段與規則)）擇一；`meal` 為 `before` / `after`。
- `qty`：一次幾顆，可以是 `0.5`。API 回應中的顆數一律是 JSON 數字。
- QR 本身含完整資料，掃描不需查詢醫院系統。
- 同成分檢查：以 `lic` 查 `drug_licenses.ingredients`（ATC 7 碼），和長輩吃藥中的藥、以及同一張藥單裡前面的藥比對。有重疊時回 `warnings: [{"type":"same_ingredient","code":"C1","with_code":"A1"}]`，前端顯示「這兩包好像是同一種藥，請問藥師」。只標示，不阻擋。

### 8.2 救命卡卡號

- 格式：`TPE-XXXX-XXXX`，`X` 取自 `23456789ABCDEFGHJKMNPQRSTUVWXYZ`（去掉 0、1、I、L、O 等容易看錯的字元），用 `secrets` 產生，約 8.5 × 10¹¹ 種組合。
- 輸入時忽略大小寫、空白和連字號。
- **QR 內容**是網址：`https://<前端網址>/c/TPE-7K3Q-9X2M`。
  - 路人用一般相機掃到：開啟前端公開頁，只顯示「這位長輩有登記救命卡，請立即撥打 119」。**這個頁面不呼叫後端**，所以無法藉此測試卡號是否存在。
  - 救護人員在台北通內掃描：前端把 `qr_code_scan` 的回覆原封不動送到 `/responder/cards/lookup`，由後端從網址取出卡號。

### 8.3 拍照辨識的輸入

App 用裝置端模型讀藥袋照片後，把整理出的欄位送到 `POST …/prescriptions/photo-preview`。看不出來的欄位留空；`confidence` 為模型對各欄位的把握（0～1，可省略，省略視為 1）：

```json
{
  "hospital": "臺北市立聯合醫院仁愛院區",
  "department": "心臟內科",
  "visit_date": "2026-11-05",
  "days": 28,
  "confidence": {"days": 0.6},
  "items": [
    {"name": "Norvasc", "license_no": null, "strength": "5 毫克", "purpose": "降血壓",
     "dose_qty": 1, "frequency": "QD", "meal_timing": "after", "confidence": {"name": 0.9}}
  ]
}
```

後端處理：

1. 有健保碼就直接查；沒有就以藥名比對健保藥品資料（產品名、主成分、中英文品名，容許錯字），相似度 0.75 以上才帶入藥品代號與劑量。
2. 每個欄位的信心分數 = 模型的把握與比對相似度取較低者；看不出來的欄位為 0，並先填預設值（一次 1 顆、早上、飯後、看診日為今天）。
3. 低於 0.8 的欄位列在 `uncertain`（例如 `items.1.name`），該藥的 `uncertain=true`，前端用紅框標示「電腦不確定這一項，請照藥袋核對」。
4. 天數看不出來時 `draft.days` 為 null，加入前必須填（否則 `400 DAYS_REQUIRED`）。

---

## 9. 技術選型

| 用途 | 套件 | 授權 |
|---|---|---|
| Web 框架 | FastAPI、Uvicorn | MIT、BSD-3 |
| 資料驗證、設定 | Pydantic、pydantic-settings | MIT |
| ORM、資料表變更 | SQLAlchemy 2.0、Alembic | MIT |
| PostgreSQL 驅動 | asyncpg | Apache-2.0 |
| JWT | PyJWT | MIT |
| 密碼雜湊 | argon2-cffi | MIT |
| 欄位加密 | cryptography | Apache-2.0 / BSD |
| 推播 | firebase-admin | Apache-2.0 |
| 測試 | pytest、pytest-asyncio、httpx | MIT、Apache-2.0、BSD-3 |
| 產生範例 QR（開發用） | segno | BSD-3 |

Python 3.12。

---

## 10. 部署

比賽規定不能使用付費服務（包含需要綁定帳單的免費額度），所以採**本地部署**：資料庫和後端用 Docker 跑在一台電腦上，Demo 用 Android Studio 模擬器。**完整步驟見 [deploy.md](deploy.md)。**

| 項目 | 設定 |
|---|---|
| 啟動 | `docker compose --profile app up -d --build`：資料庫＋後端；後端啟動時自動更新資料表、匯入範例資料（含之後 2 週門診） |
| 資料庫 | PostgreSQL 17（Docker，資料存在 volume `pgdata`） |
| 排程 | **後端內建**，啟動後每分鐘執行一次 `TickService`（`SCHEDULER_ENABLED=true`）；`POST /api/v1/internal/tick` 保留給手動測試 |
| App 連線 | 模擬器以 `http://10.0.2.2` 連到電腦本機；App 只在 debug 版允許這兩個網址使用 http（`android/app/src/debug/res/xml/network_security_config.xml`） |
| 推播 | Firebase Spark（免費、不綁卡）的 Cloud Messaging，服務帳戶金鑰放 `backend/secrets/`；未設定時推播內容寫在後端 log |
| 健康檢查 | `GET /health` |

原本規劃的雲端部署（Cloud Run、Render 等）已取消。

**環境變數**（`.env`，由 `uv run python -m scripts.init_env` 從 `.env.example` 建立並產生金鑰）

| 名稱 | 說明 |
|---|---|
| `DATABASE_URL` | PostgreSQL 連線字串；用 docker compose 啟動後端時自動改為連 `db` 容器 |
| `JWT_SECRET` | JWT 簽章金鑰 |
| `FIELD_ENCRYPTION_KEY` | Fernet 金鑰；開始存資料後不可更換、不可遺失 |
| `INTERNAL_SECRET` | 手動呼叫 `/internal/tick` 的密鑰 |
| `FIREBASE_CREDENTIALS` | 空白＝推播只寫 log；否則為 Firebase 服務帳戶金鑰（檔案路徑如 `secrets/firebase.json`，或 JSON 內容） |
| `FRONTEND_BASE_URL` | 前端網址，預設 `http://10.0.2.2:5173`（模擬器）：CORS、推播 deeplink、救命卡與邀請 QR |
| `EXTRA_CORS_ORIGINS` | 額外允許的網頁來源，預設 `http://localhost:5173`（電腦瀏覽器） |
| `SCHEDULER_ENABLED` | 後端內建排程，預設 `true` |
| `DEMO_MODE` | 開啟後可切換身分、使用模擬觸發 API |

---

## 11. Demo 資料與展示用功能

### 11.1 種子資料（`seed/`）

- 長輩、家人各一個模擬台北通帳號（修改 `account.json` 的 `birthday`、`citizen` 呈現長輩情境）。
- 消防局名冊 3 筆：`A12345`（大安分隊）、`A23456`（中山分隊）在職且有救護權限；`A34567`（信義分隊）已離職，示範被擋。分隊清單為範例名稱。
- 聯醫院區、科別、醫師、未來 2 週門診與看診時間（每 30 分鐘一個，每個 8 個名額，預先填入部分模擬預約；含一個全部額滿、一個停診的門診）。✅ 院區名稱與地址依北市聯醫公開資訊，科別、醫師、門診為模擬資料；門診從執行匯入的隔天起產生 2 週，Demo 前一天要再執行一次。
- 範例藥袋 QR 3 張（v2，一張藥單多個藥），對應 UI 的藥單 A、B，以及和 A1 同成分的藥單 C。✅ `seed/qr/`
- 藥品資料：匯入健保用藥品項全部 4.5 萬筆（真實資料）；範例藥袋用真實藥品代號。北市聯醫常用藥清單為模擬。✅

### 11.2 展示用 API（僅 `DEMO_MODE`，正式版移除）

| 方法 | 路徑 | 說明 |
|---|---|---|
| POST | `/demo/trigger/reminder?elder_id=` | 立即提醒今天第一個有藥的時段，長輩與家屬同時收到（已提醒過就再推播一次） |
| POST | `/demo/trigger/refill?elder_id=` | 立即發回診提醒（最快吃完的那幾張藥單） |

**Demo 順序**：路人掃 QR 只看到「請撥 119」→ 救護人員登入後掃同一張卡看到完整資料 → 女兒手機收到「救護人員查看了媽媽的救命卡」。

---

## 12. 需要 App 與前端配合

| 項目 | 負責 | 說明 |
|---|---|---|
| FCM 推播 | App | 加入 `firebase_messaging`；新增 Handler 回傳 FCM token；處理通知點擊的 deeplink |
| 全螢幕提醒 | App | 聲音、震動、閃光、全螢幕顯示 |
| 國台語朗讀 | 前端、App | 國語用 `microservice/frontend/tts/`（`speak(speech_text)`：App 的 `tts_speak` handler → 網頁 speechSynthesis，見該目錄 README）；App 已加 `tts_speak`、`tts_stop` handler（`lib/util/web_message_handler/tts_message_handler.dart`，`flutter_tts`，只用離線語音）；Android WebView 不支援 speechSynthesis，只能靠 App handler；英文稿 `speech_text_en` 要用 `speak(text, { lang: 'en-US' })` 朗讀，**前端模組與 App handler 目前只挑中文語音，需要補上英文（en-US）離線語音的選擇**；台語之後再定 |
| 拍照辨識 | App | 拍照走台北通原生 handler（WebView 直接開相機可能失敗）；用裝置端模型（例如 Gemma 4 E2B）把照片整理成 [§8.3](#83-拍照辨識的輸入) 的欄位，再由前端送到 `photo-preview`；README 要揭露模型名稱、版本、量化格式、推論框架與來源 |
| 救護人員查詢 | 前端 | UI R02 的「身分證字號」改為救命卡卡號輸入（或掃 QR） |
| 卡號 QR 與桌布 | 前端 | 依卡號產生 QR、敬老卡貼紙、手機桌布 |
| 救護人員定位 | 前端 | 查詢前呼叫台北通 `location` 取得座標 |
| 一鍵撥號 | 前端 | 呼叫台北通 `phone_call` |
| 帶我去醫院 | 前端 | 呼叫台北通 `launch_map` |

---

## 13. 下一期

- 新增藥品：帶入聯醫用藥（模擬 API）。
- 複方藥的同成分比對（複方有自己的 ATC，目前不會和單方比對到）。
- 串接北市聯醫掛號系統、消防局人員名冊正式 API。
- 台北通 userinfo 的伺服器端驗證（比賽時直接信任前端送來的 userinfo）。
