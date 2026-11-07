# emergency_card — 救命卡

功能規格「二、救命卡」2-1～2-3：長輩的醫療資訊、隨機卡號、健康資料同意、救護人員查看紀錄與通知家人。規格書 §5.4、§8.2。

**狀態**：✅ 完成（測試：`tests/test_emergency_card.py`）

## API

| 方法 | 路徑 | 權限 | 說明 |
|---|---|---|---|
| GET | `/emergency-card/common-items` | 不需登入 | 常見慢性病、過敏選項，減少打字 |
| POST | `/elders/{elder_id}/consents` | 寫 | 勾選同意儲存健康資料（寫入救命卡前必須）；已同意時回傳原紀錄 |
| DELETE | `/elders/{elder_id}/consents/health_data` | **長輩本人** | 撤回：清空病史、過敏，卡號失效；聯絡人、查看紀錄保留 |
| GET | `/elders/{elder_id}/emergency-card` | 讀 | 長輩、家人檢視 |
| PUT | `/elders/{elder_id}/emergency-card` | 寫 | 第一次儲存時建立救命卡並產生卡號 |
| PUT | `/elders/{elder_id}/emergency-card/contacts` | 寫 | 整批設定緊急聯絡人（最多 2 位） |
| POST | `/elders/{elder_id}/emergency-card/regenerate-code` | 讀 | 卡片遺失或外流時重新產生，舊卡號立即失效。依功能規格 2-3，**任何綁定的家人都可以**（包含已完成初始設定的家人） |

「寫」＝長輩本人，或尚未完成初始設定的家人；「讀」＝長輩本人或任何綁定的家人（family 模組 `ensure_access`）。

## 救命卡內容（CardOut）

| 欄位 | 說明 |
|---|---|
| `title`、`birth_year`、`gender` | 稱呼（如「陳阿嬤」）、出生年、性別 |
| `current_medications` | 正在吃的藥，由 medication 模組自動帶入 |
| `chronic_conditions`、`allergies` | 慢性病、過敏（藥物或食物），加密儲存 |
| `contacts` | 緊急聯絡人，每位附 `call`（App 的 `phone_call` 訊息） |
| `hospital` | 預設「臺北市立聯合醫院」 |
| `code` | `code` 卡號（印在貼紙上）、`qr_url` QR 內容（敬老卡背面貼紙、手機桌布）；撤回同意後為 `null` |
| `has_consent` | 是否已同意儲存健康資料 |
| `access_logs` | 查看紀錄：救護人員、分隊、方式、地點、時間（新的在前，最多 50 筆） |

貼紙與桌布的圖由前端依 `code`、`qr_url` 產生。

## 救護人員查詢（由 responder 模組呼叫）

`lookup_for_responder(responder, code, method, latitude, longitude)`：

1. 用有效卡號找到救命卡，找不到回 `404 CARD_NOT_FOUND`
2. 寫查看紀錄（救護人員姓名、分隊存快照）
3. 回傳 `ResponderCardOut`：過敏 → 正在吃的藥 → 慢性病 → 緊急聯絡人、免責文字、`close_at`（30 分鐘後）
4. 紀錄寫入後，推播每位綁定家人：「臺北市消防局中山分隊王大明於 15:20 查看了媽媽的救命卡」，`data.call` 為撥給該分隊的 `phone_call` 訊息。推播失敗不影響救護人員查看

## 提供給其他模組

- `elder_title(elder_id)`：稱呼與性別（吃藥提醒語音、「打給她／他」）

## 錯誤

| code | HTTP | 情況 |
|---|---|---|
| `CONSENT_REQUIRED` | 403 | 還沒同意就要儲存或重新產生卡號 |
| `ELDER_ONLY` | 403 | 家人要撤回同意 |
| `CARD_NOT_CREATED` | 404 | 還沒建立救命卡 |
| `CARD_NOT_FOUND` | 404 | 卡號無效或已失效 |
| `READ_ONLY`、`NOT_BOUND` | 403 | 見 family 模組 |

## 檔案

- `rules.py`：產生卡號（`TPE-XXXX-XXXX`）、卡號正規化、QR 網址、從 QR 取出卡號、常見選項、免責文字

## 資料表

- `emergency_cards`：慢性病、過敏加密儲存
- `emergency_contacts`：姓名、電話加密儲存
- `card_codes`：卡號紀錄，每張卡只有一組有效
- `card_access_logs`：查看紀錄，只能新增
- `consents`：同意紀錄（同意者、時間、撤回時間）

## 依賴

- `family`：權限、要通知的家人與稱呼
- `medication`：正在吃的藥
- `notification`：推播
- `integrations/townpass`：`PhoneCallMessage`
