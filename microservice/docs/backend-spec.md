# 呷藥囉｜後端開發規格書

> 版本：v0.1（2026-11-07）
> 範圍：後端 API（Python FastAPI）。前端架構不在本文件範圍，只列出前端與 App 需要配合的事項。
> 依據：功能規格（文字版）與交付規格（圖檔版）。兩者矛盾處的決議見 [§1.2](#12-規格決議)。

---

## 1. 總覽

### 1.1 產品範圍

呷藥囉在台北通內分成三區：

| 區 | 功能 | 本期 |
|---|---|---|
| 藥 | 藥品清單、掃藥袋 QR 新增、吃藥提醒、家人綁定與通知 | ✅ |
| 救命卡 | 長輩醫療資訊、隨機卡號、救護人員查看、查看紀錄與通知家人 | ✅ |
| 回診（Bonus） | 用藥天數算回診提醒、聯醫預約（模擬資料） | ✅ |

### 1.2 規格決議

文字版與圖檔版矛盾處，決議如下：

| # | 項目 | 決議 |
|---|---|---|
| 1 | 名稱 | **呷藥囉** |
| 2 | 救護人員查詢方式 | **隨機卡號**（`TPE-XXXX-XXXX`），不用身分證字號 |
| 3 | 提醒時段 | **可修改**，預設值見 [§5.3](#53-提醒時段與分配規則) |
| 4 | 藥品標示 | **數字**（1、2、3…），寫在藥袋上 |
| 5 | 緊急聯絡人 | **最多 2 位** |
| 6 | 家人權限 | **唯讀**；但每次綁定後有**一次**初始設定機會，見 [§3.2](#32-家人的初始設定) |
| 7 | 新增藥品方式 | 本期**只做掃藥袋 QR**；聯醫用藥帶入、手動輸入列為下一期 |
| 8 | 藥師角色 | **不需要** |

圖檔版的「拍照辨識」（E05、E06c）不做。

### 1.3 比賽規則對後端的限制

- **AI 推論在裝置端**：後端不呼叫任何雲端 AI API。語音（TTS、台語錄音拼接）由前端處理，後端只提供結構化資料。
- **開源免費**：所有套件需為 MIT、BSD、Apache-2.0 等可納入 AGPL 的授權，見 [§9](#9-技術選型)。
- **可移轉、可維運**：附 Dockerfile，依 README 即可建置。

---

## 2. 系統架構

```
┌──────────────┐  flutterObject   ┌────────────────┐   HTTPS/JSON   ┌──────────────────┐
│ 城市通 App    │ ◀──────────────▶ │ 微服務網頁       │ ─────────────▶ │ 後端 API          │
│ (Flutter)    │                  │ (WebView)      │                │ FastAPI@Cloud Run│
└──────▲───────┘                  └────────────────┘                └───┬──────┬───────┘
       │ FCM 推播                                                       │      │
       └────────────────────────────────────────────────────────────────┘      │
                                                                               ▼
                                     ┌──────────────────┐            ┌──────────────────┐
                                     │ Cloud Scheduler  │──每分鐘───▶│ PostgreSQL        │
                                     │ POST /internal/  │  呼叫 API  │ (Supabase / Neon) │
                                     │      tick        │            └──────────────────┘
                                     └──────────────────┘
```

### 2.1 推播（需要 App 修改）

城市通內建的 `notify` 只能顯示**本機通知**（`flutter_local_notifications`），伺服器無法透過它通知其他人的手機。以下功能都需要伺服器推播：

- 吃藥提醒（時間到通知長輩）
- 長輩回應、3 次沒回應 → 通知家人
- 救護人員查看救命卡 → 通知家人
- 回診提醒

**做法**：App 加入 `firebase_messaging`（BSD-3），並依入門指引「以自訂 Handler 擴充 App 能力」的四個步驟新增 `push_token` Handler（見 [§2.3](#23-與城市通-app-的溝通)），把 FCM token 交給網頁，網頁再呼叫 `POST /devices` 登記。後端用 `firebase-admin` 發送。

### 2.2 排程

Cloud Run 沒有請求時會縮到 0 台，程式內的排程器（APScheduler）不可靠。改用 **Cloud Scheduler 每分鐘呼叫 `POST /internal/tick`**，由後端檢查到期的提醒。詳見 [§6](#6-排程與推播)。

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
| `qr_code_scan` | App → 後端 | `POST …/medications/qr-preview`、`POST /responder/cards/lookup`、`POST /family/bindings` | 掃到的字串；使用者取消時為 `null` |
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
| 長輩 `elder` | 台北通 userinfo | 管理自己的藥、提醒時段、救命卡、家人綁定、預約 |
| 家人 `family` | 台北通 userinfo | 以邀請碼綁定長輩；唯讀（初始設定除外） |
| 救護人員 `responder` | 消防局帳號（模擬 EMT-001～003） | 只能查看救命卡；登入 12 小時有效 |
| 路人 | 不登入 | 掃 QR 只看到「請撥打 119」，不呼叫後端 |

身分在第一次使用時選擇（長輩或家人），存在 `users.role`。

### 3.1 權限矩陣

| 資源 | 長輩本人 | 已綁定家人 | 救護人員 |
|---|---|---|---|
| 藥品清單 | 讀寫 | 讀（初始設定時可寫） | — |
| 提醒時段 | 讀寫 | 讀（初始設定時可寫） | — |
| 提醒回應 | 寫（按「好，我知道了」） | 讀；可「提醒長輩吃藥」 | — |
| 救命卡、緊急聯絡人 | 讀寫 | 讀（初始設定時可寫） | 讀（需卡號） |
| 救命卡重新產生卡號 | 可 | 可 | — |
| 救命卡查看紀錄 | 讀 | 讀 | — |
| 家人綁定 | 產生邀請碼、解除 | 使用邀請碼 | — |
| 預約回診 | 讀寫 | 讀 | — |

「重新產生卡號」開放給家人，因為卡片遺失時可能是家人發現。

### 3.2 家人的初始設定

- 每一筆綁定（`family_bindings`）都有一次初始設定機會。
- 綁定成功後，家人可以新增或修改：藥品、提醒時段、救命卡、緊急聯絡人。
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
    │   ├── medication/          # 藥品、QR 解析、同成分檢查、時段
    │   ├── reminder/            # 提醒事件、回應、升級通知家人
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
        ├── fda/                 # 食藥署藥品許可證（匯入的開放資料）
        └── fcm/                 # Firebase Cloud Messaging
```

---

## 5. 資料庫設計

### 5.1 選擇

- **PostgreSQL**：資料關聯強（使用者、綁定、藥品、預約、紀錄），且需要交易（邀請碼只能用一次、門診名額）。
- **代管**：Supabase 或 Neon 免費方案。Cloud Run 會縮到 0 台，不能用 SQLite；Cloud SQL 沒有免費方案。
- **本機開發**：Docker 執行 `postgres:17`。
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
| notify_on_ack | bool default true | 長輩每次回應是否通知（可關） |
| setup_completed_at | timestamptz NULL | NULL 表示還能做初始設定 |
| created_at | timestamptz | |
| revoked_at | timestamptz NULL | 解除綁定 |

唯一索引：`(elder_id, family_id) WHERE revoked_at IS NULL`。

#### 藥

**`medications`**

| 欄位 | 型別 | 說明 |
|---|---|---|
| id | uuid PK | |
| elder_id | uuid FK users | |
| number | int | 藥袋上的大編號 |
| name | text | 藥名 |
| license_no | text NULL | 許可證字號，用於同成分檢查 |
| purpose | text | 用途 |
| dose_qty | numeric(3,1) | 一次幾顆，支援半顆 |
| frequency | enum `QD` / `BID` / `TID` / `QID` / `HS` | 一天 1～4 次、睡前 |
| meal_timing | enum `before` / `after` / `bedtime` | 飯前、飯後、睡前 |
| start_date | date | 就醫日期 |
| days | int | 給藥天數 |
| hospital | text | 院區 |
| department | text | 科別 |
| doctor | text | 醫師 |
| source | enum `qr` / `tpech` / `manual` | 本期只有 `qr` |
| status | enum `active` / `stopped` | |
| stopped_at | timestamptz NULL | |
| created_by | uuid FK users | 長輩或做初始設定的家人 |
| created_at / updated_at | timestamptz | |

唯一索引：`(elder_id, number) WHERE status = 'active'`。

**`time_slots`**：每位長輩 7 筆，預設值見 [§5.3](#53-提醒時段與分配規則)。

| 欄位 | 型別 | 說明 |
|---|---|---|
| elder_id | uuid FK users | PK 之一 |
| slot_key | enum | PK 之一，見下表 |
| time | time | 可修改 |

**`drug_licenses`**：從食藥署開放資料匯入，只讀。

| 欄位 | 型別 | 說明 |
|---|---|---|
| license_no | text PK | 許可證字號 |
| name_zh / name_en | text | 中、英文品名 |
| ingredients | text[] | 主成分（正規化後） |

#### 提醒

**`reminder_events`**：每個時段每天一筆。

| 欄位 | 型別 | 說明 |
|---|---|---|
| id | uuid PK | |
| elder_id | uuid FK users | |
| slot_key | enum | |
| scheduled_at | timestamptz | 該次提醒時間 |
| items | jsonb | 快照：`[{"number":1,"name":"…","qty":2}]` |
| attempts | int | 已推播次數（1～3） |
| last_pushed_at | timestamptz | |
| acked_at | timestamptz NULL | 長輩按「好，我知道了」 |
| escalated_at | timestamptz NULL | 已通知家人「沒有回應」 |

唯一索引：`(elder_id, slot_key, scheduled_at)`，避免排程重複建立。

#### 救命卡

**`emergency_cards`**：每位長輩一張。

| 欄位 | 型別 | 說明 |
|---|---|---|
| id | uuid PK | |
| elder_id | uuid FK users UNIQUE | |
| title | text | 稱呼，如「陳阿嬤」；吃藥提醒語音也使用 |
| birth_year | int | |
| gender | enum | |
| chronic_conditions | text 🔒 | JSON 陣列，加密後儲存 |
| allergies | text 🔒 | JSON 陣列：`[{"type":"drug","name":"盤尼西林"}]` |
| hospital | text | 預設「臺北市立聯合醫院」 |
| updated_at / updated_by | | |

「正在吃的藥」不存在這張表，查詢時由 `MedicationService` 即時帶入。

**`emergency_contacts`**：每張卡最多 2 筆（service 檢查）。

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
| account | text UNIQUE | `EMT-001`～`EMT-003` |
| password_hash | text | argon2 |
| name | text | |
| unit | text | 所屬分隊，如「中山分隊」 |
| title | text | 職稱 |
| employment_status | enum `active` / `resigned` | |
| has_ems_permission | bool | 是否有救護權限 |

正式版名冊由消防局提供，透過 `integrations/fire_dept` 查詢；比賽時直接讀這張表。

#### 回診

| 資料表 | 主要欄位 | 說明 |
|---|---|---|
| `hospitals` | id、name、address | 聯醫院區：中興、仁愛、和平、婦幼、忠孝、陽明、松德、林森、昆明 |
| `departments` | id、hospital_id、name | 科別 |
| `doctors` | id、department_id、name | 醫師 |
| `clinic_sessions` | id、doctor_id、date、period（`morning` / `afternoon` / `evening`）、capacity、booked_count、status（`open` / `suspended`） | 門診；額滿或停診時前端顯示灰色 |
| `appointments` | id、elder_id、session_id、visit_no（看診號碼）、status（`booked` / `cancelled`）、created_at | |

預約時以 `UPDATE clinic_sessions SET booked_count = booked_count + 1 WHERE id = ? AND booked_count < capacity AND status = 'open'` 確保不超額，`visit_no` 取更新後的 `booked_count`。

#### 推播

**`device_tokens`**：user_id、token（UNIQUE）、platform、updated_at。一個使用者可以有多台裝置。

### 5.3 提醒時段與分配規則

**預設時段**（每位長輩可修改）：

| slot_key | 名稱 | 預設 |
|---|---|---|
| `breakfast_before` | 早餐飯前 | 07:30 |
| `breakfast_after` | 早餐飯後 | 08:00 |
| `lunch_before` | 午餐飯前 | 11:30 |
| `lunch_after` | 午餐飯後 | 12:00 |
| `dinner_before` | 晚餐飯前 | 17:30 |
| `dinner_after` | 晚餐飯後 | 18:00 |
| `bedtime` | 睡前 | 21:00 |

**分配規則**（`medication/rules.py`）：

| 頻率 | 分配到的餐別 |
|---|---|
| `QD` 一天一次 | 早 |
| `BID` 一天兩次 | 早、晚 |
| `TID` 一天三次 | 早、中、晚 |
| `QID` 一天四次 | 早、中、晚、睡前 |
| `HS` 睡前 | 睡前 |

餐別再依 `meal_timing` 對應到飯前或飯後時段。例如「TID、飯後」→ `breakfast_after`、`lunch_after`、`dinner_after`。分配結果即時計算，不另外存表。

**其他計算規則**：

- **剩餘天數** = `start_date + days − 今天`，小於 0 顯示 0。
- **藥吃完日** = `start_date + days − 1`。
- **編號** = 該長輩目前 `active` 藥品中，沒被使用的最小正整數。停用後編號釋放，讓編號維持在長輩好記的小數字。

### 5.4 個資保護

- 慢性病、過敏、用藥屬個資法第 6 條特種個資。救命卡寫入前必須有有效的 `consents`（`health_data`），否則回 `403 CONSENT_REQUIRED`。
- **撤回同意**：清空 `chronic_conditions`、`allergies`，並撤銷有效卡號。查看紀錄保留。
- **欄位加密**：🔒 欄位用 `cryptography` 的 Fernet（AES-128-CBC + HMAC）在應用層加密，金鑰放環境變數 `FIELD_ENCRYPTION_KEY`（正式版放 Secret Manager）。
- **查看紀錄**只能新增。
- 救護人員查詢回應附上免責文字：「本資料由本人或家屬提供，僅供參考，請以醫療專業判斷為準」。
- 電子同意的形式需請法律專業確認（交付規格第 9 點）。

---

## 6. 排程與推播

### 6.1 `/internal/tick`

Cloud Scheduler 每分鐘呼叫一次，用 OIDC token 驗證呼叫者（本機開發改用 `X-Internal-Secret` header）。每次執行以下工作，每項都要可以重複執行而不重複發送：

| 工作 | 條件 | 動作 |
|---|---|---|
| 建立提醒 | 某長輩某時段時間已到，且該時段有藥、今天還沒建立 | 建 `reminder_events`，推播長輩（第 1 次） |
| 重新提醒 | 未回應，距上次推播滿 10 分鐘，`attempts < 3` | 推播長輩，`attempts + 1` |
| 通知家人沒有回應 | 未回應，第 3 次推播後滿 10 分鐘，尚未通知 | 推播所有綁定家人，附長輩電話；寫入 `escalated_at` |
| 回診提醒 | 每天 09:00；有藥品的吃完日 = 今天 + 7 | 推播長輩與家人：「1 號、3 號的藥再 7 天就吃完囉，要記得回診或領慢箋」 |
| 預約提醒 | 預約前一天 18:00、當天 08:00 | 推播長輩與家人 |

重新提醒的間隔（10 分鐘）先用預設值，Demo 時可用環境變數縮短。

### 6.2 推播內容

推播一律帶 `data` 欄位，讓 App 點開後導到對應頁面：

```json
{
  "type": "medication_reminder",
  "event_id": "…",
  "deeplink": "https://<前端網址>/reminder/<event_id>"
}
```

| type | 對象 | 文字範例 |
|---|---|---|
| `medication_reminder` | 長輩 | 阿嬤，吃藥時間到囉～飯後吃：1 號 2 顆、3 號 1 顆 |
| `medication_acked` | 家人（`notify_on_ack`） | 媽媽 18:00 已經吃藥了 |
| `medication_no_response` | 家人 | 媽媽 18:00 的吃藥提醒沒有回應，要不要打給她？ |
| `medication_nudge` | 長輩 | 女兒提醒你吃藥喔 |
| `card_accessed` | 家人 | 臺北市消防局中山分隊王大明於 15:20 查看了媽媽的救命卡 |
| `refill_reminder` | 長輩、家人 | 1 號、3 號的藥再 7 天就吃完囉 |
| `appointment_reminder` | 長輩、家人 | 明天上午 仁愛院區 家醫科 林醫師 |

全螢幕提醒、聲音、震動、閃光、國台語朗讀由 App 與前端處理，後端只提供 `items` 與稱呼。

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
| 409 | `Conflict`（邀請碼已使用、門診額滿、緊急聯絡人已滿） |
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
| PATCH | `/family/bindings/{id}` | 家人修改 `notify_on_ack`、`relation_label` |
| POST | `/family/bindings/{id}/complete-setup` | 家人完成初始設定，之後唯讀 |
| DELETE | `/family/bindings/{id}` | 長輩解除綁定 |

**medication**

| 方法 | 路徑 | 說明 |
|---|---|---|
| GET | `/elders/{elder_id}/medications` | 藥品清單（含時段、剩餘天數） |
| POST | `/elders/{elder_id}/medications/qr-preview` | body 為 App 的 `qr_code_scan` 回覆；回解析結果與同成分警示（不寫入） |
| POST | `/elders/{elder_id}/medications` | 確認後加入，回編號與「請在藥袋上寫上大大的 N」 |
| GET | `/elders/{elder_id}/medications/{id}` | 詳細頁 |
| PATCH | `/elders/{elder_id}/medications/{id}` | 編輯 |
| POST | `/elders/{elder_id}/medications/{id}/stop` | 停用 |
| GET | `/elders/{elder_id}/time-slots` | 時段設定 |
| PUT | `/elders/{elder_id}/time-slots` | 修改時段 |
| GET | `/elders/{elder_id}/next-dose` | 首頁狀態列：「下一次吃藥：今天 12:00」 |

**reminder**

| 方法 | 路徑 | 說明 |
|---|---|---|
| GET | `/reminders/{event_id}` | 提醒畫面資料：稱呼、時段、`items` |
| POST | `/reminders/{event_id}/ack` | 長輩按「好，我知道了」 |
| GET | `/elders/{elder_id}/reminders?date=` | 某天的提醒與回應狀態 |
| POST | `/elders/{elder_id}/nudge` | 家人提醒長輩吃藥 |

**emergency_card**

| 方法 | 路徑 | 說明 |
|---|---|---|
| POST | `/elders/{elder_id}/consents` | 同意儲存健康資料 |
| DELETE | `/elders/{elder_id}/consents/health_data` | 撤回同意 |
| GET | `/elders/{elder_id}/emergency-card` | 長輩、家人檢視（含正在吃的藥、查看紀錄） |
| PUT | `/elders/{elder_id}/emergency-card` | 編輯 |
| PUT | `/elders/{elder_id}/emergency-card/contacts` | 設定緊急聯絡人（最多 2 位） |
| POST | `/elders/{elder_id}/emergency-card/regenerate-code` | 重新產生卡號，舊卡號立即失效 |
| GET | `/emergency-card/common-items` | 常見慢性病、過敏選項 |

**responder**

| 方法 | 路徑 | 說明 |
|---|---|---|
| POST | `/responder/login` | 帳號密碼登入，比對名冊；不符回 `403 RESPONDER_NOT_AUTHORIZED` |
| POST | `/responder/cards/lookup` | body：`qr`（App 的 `qr_code_scan` 回覆）或 `code`（手動輸入）擇一，加上 `location`（App 的 `location` 回覆）；回救命卡內容；寫查看紀錄並推播家人 |

查詢回應依顯示順序排列：過敏 → 正在吃的藥 → 慢性病 → 緊急聯絡人，並附免責文字。每位救護人員每分鐘最多查詢 10 次，避免猜卡號。

**appointment**

| 方法 | 路徑 | 說明 |
|---|---|---|
| GET | `/hospitals` | 院區清單 |
| GET | `/hospitals/{id}/departments?elder_id=` | 科別；上次看的科別排第一 |
| GET | `/departments/{id}/doctors?elder_id=` | 醫師；標記上次看診的醫師 |
| GET | `/doctors/{id}/sessions` | 未來 2 週門診（日期、時段、是否可約） |
| POST | `/elders/{elder_id}/appointments` | 預約 |
| GET | `/elders/{elder_id}/appointments` | 我的預約 |
| POST | `/elders/{elder_id}/appointments/{id}/cancel` | 取消 |

**notification、internal**

| 方法 | 路徑 | 說明 |
|---|---|---|
| POST | `/devices` | body 為 App 的 `push_token` 回覆；登記 FCM token |
| DELETE | `/devices/{token}` | 移除 token |
| POST | `/internal/tick` | 排程入口，見 [§6.1](#61-internaltick) |

---

## 8. 格式定義

### 8.1 藥袋 QR

比賽時自行產生範例 QR。一張藥袋一個 QR，內容為 JSON：

```json
{
  "v": 1,
  "t": "rx",
  "hosp": "臺北市立聯合醫院仁愛院區",
  "dept": "家醫科",
  "dr": "林醫師",
  "date": "2026-11-07",
  "days": 28,
  "lic": "衛署藥製字第012345號",
  "name": "脈優錠 5 毫克",
  "use": "降血壓",
  "qty": 1,
  "freq": "QD",
  "meal": "after"
}
```

- `v`：格式版本，不支援的版本回 `400`。
- QR 本身含完整資料，掃描不需查詢醫院系統。前端可離線顯示確認畫面，加入清單時才呼叫後端。
- 同成分檢查：以 `lic` 查 `drug_licenses.ingredients`，和長輩其他 `active` 藥品比對。有重疊時回 `warnings: [{"type":"same_ingredient","with_number":2}]`，前端顯示「這兩包好像是同一種藥，請問藥師」。只標示，不阻擋。

### 8.2 救命卡卡號

- 格式：`TPE-XXXX-XXXX`，`X` 取自 `23456789ABCDEFGHJKMNPQRSTUVWXYZ`（去掉 0、1、I、L、O 等容易看錯的字元），用 `secrets` 產生，約 8.5 × 10¹¹ 種組合。
- 輸入時忽略大小寫、空白和連字號。
- **QR 內容**是網址：`https://<前端網址>/c/TPE-7K3Q-9X2M`。
  - 路人用一般相機掃到：開啟前端公開頁，只顯示「這位長輩有登記救命卡，請立即撥打 119」。**這個頁面不呼叫後端**，所以無法藉此測試卡號是否存在。
  - 救護人員在台北通內掃描：前端把 `qr_code_scan` 的回覆原封不動送到 `/responder/cards/lookup`，由後端從網址取出卡號。

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

Python 3.12。

---

## 10. 部署

| 項目 | 設定 |
|---|---|
| 後端 | Cloud Run，`asia-east1`，`gcloud run deploy --source microservice/backend` |
| 資料庫 | Supabase 或 Neon 免費方案（PostgreSQL） |
| 排程 | Cloud Scheduler，每分鐘 `POST /api/v1/internal/tick` |
| 推播 | Firebase 專案（可和前端 Hosting 同一個） |

**環境變數**

| 名稱 | 說明 |
|---|---|
| `DATABASE_URL` | PostgreSQL 連線字串 |
| `JWT_SECRET` | JWT 簽章金鑰 |
| `FIELD_ENCRYPTION_KEY` | Fernet 金鑰 |
| `FIREBASE_CREDENTIALS` | 服務帳戶 JSON（Cloud Run 上可改用預設憑證） |
| `INTERNAL_SECRET` | 本機呼叫 `/internal/tick` 用 |
| `FRONTEND_BASE_URL` | 推播 deeplink 與救命卡 QR 網址 |
| `REMIND_INTERVAL_MINUTES` | 重新提醒間隔，預設 10 |
| `DEMO_MODE` | 開啟後可切換身分、使用模擬觸發 API |

Dockerfile 啟動時讀取 Cloud Run 提供的 `PORT`。

---

## 11. Demo 資料與展示用功能

### 11.1 種子資料（`seed/`）

- 長輩、家人各一個模擬台北通帳號（修改 `account.json` 的 `birthday`、`citizen` 呈現長輩情境）。
- 消防局名冊 3 筆：`EMT-001`、`EMT-002` 在職且有救護權限；`EMT-003` 已離職，示範被擋。
- 聯醫院區、科別、醫師、未來 2 週門診（含一個額滿、一個停診）。
- 範例藥袋 QR 3 張，其中 2 張成分相同，示範同成分警示。
- 食藥署許可證資料：只匯入範例藥品需要的幾筆。

### 11.2 展示用 API（僅 `DEMO_MODE`，正式版移除）

| 方法 | 路徑 | 說明 |
|---|---|---|
| POST | `/demo/trigger/reminder` | 立即觸發長輩的吃藥提醒 |
| POST | `/demo/trigger/no-response` | 立即觸發「沒有回應」通知家人 |
| POST | `/demo/trigger/refill` | 立即觸發回診提醒 |

**Demo 順序**：路人掃 QR 只看到「請撥 119」→ 救護人員登入後掃同一張卡看到完整資料 → 女兒手機收到「救護人員查看了媽媽的救命卡」。

---

## 12. 需要 App 與前端配合

| 項目 | 負責 | 說明 |
|---|---|---|
| FCM 推播 | App | 加入 `firebase_messaging`；新增 Handler 回傳 FCM token；處理通知點擊的 deeplink |
| 全螢幕提醒 | App | 聲音、震動、閃光、全螢幕顯示 |
| 國台語朗讀 | 前端 | 國語用手機內建 TTS，台語用預錄句子拼接 |
| 卡號 QR 與桌布 | 前端 | 依卡號產生 QR、敬老卡貼紙、手機桌布 |
| 救護人員定位 | 前端 | 查詢前呼叫台北通 `location` 取得座標 |
| 一鍵撥號 | 前端 | 呼叫台北通 `phone_call` |
| 帶我去醫院 | 前端 | 呼叫台北通 `launch_map` |

---

## 13. 下一期

- 新增藥品：帶入聯醫用藥（模擬 API）、手動輸入。
- 串接北市聯醫掛號系統、消防局人員名冊正式 API。
- 台北通 userinfo 的伺服器端驗證（比賽時直接信任前端送來的 userinfo）。
