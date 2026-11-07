# emergency_card — 救命卡

功能規格「二、救命卡」2-1～2-3：長輩的醫療資訊、隨機卡號、健康資料同意、救護人員查看紀錄與通知家人。規格書 §5.4、§8.2。

**狀態**：✅ 完成（測試：`tests/test_emergency_card.py`）

## API

| 方法 | 路徑 | 權限 | 說明 |
|---|---|---|---|
| GET | `/emergency-card/common-items` | 不需登入 | 常見慢性病、過敏選項，減少打字 |
| POST | `/elders/{elder_id}/consents` | 寫 | 勾選同意儲存健康資料（寫入救命卡前必須）；已同意時回傳原紀錄 |
| DELETE | `/elders/{elder_id}/consents/health_data` | **長輩本人** | 撤回：清空病史、過敏，卡號失效；姓名、聯絡人、查看紀錄保留 |
| GET | `/elders/{elder_id}/emergency-card` | 讀 | 長輩、家人檢視（UI E13、F06） |
| PUT | `/elders/{elder_id}/emergency-card` | 寫 | 儲存整張卡（UI E14）：姓名、出生年月日、一位緊急聯絡人必填。第一次儲存時建立救命卡並產生卡號 |
| POST | `/elders/{elder_id}/emergency-card/regenerate-code` | 讀 | 卡片遺失或外流時重新產生，舊卡號立即失效。依功能規格 2-3，**任何綁定的家人都可以**（包含已完成初始設定的家人） |

「寫」＝長輩本人，或尚未完成初始設定的家人；「讀」＝長輩本人或任何綁定的家人（family 模組 `ensure_access`）。

## 救命卡內容（CardOut）

| 欄位 | 說明 |
|---|---|
| `name`、`birth_date`、`age`、`gender`、`blood_type` | 姓名（加密）、出生年月日、年齡（例如 78）、性別、血型（A、B、O、AB、不知道） |
| `contact` | 緊急聯絡人（一位），附 `call`（App 的 `phone_call` 訊息） |
| `chronic_conditions`、`allergies` | 慢性病、過敏（藥物、食物），本人填寫，加密儲存 |
| `special`、`language` | 特殊狀況（加密儲存）、慣用語言 |
| `current_medications` | 目前用藥（A1 等），來自藥單，不能手動編輯 |
| `code` | `code` 卡號（印在貼紙上）、`qr_url` QR 內容（敬老卡背面貼紙、手機桌布）；撤回同意後為 `null` |
| `has_consent` | 是否已同意儲存健康資料 |
| `access_logs` | 查看紀錄：救護人員、分隊、人員編號、方式、地點、時間（新的在前，最多 50 筆） |

不收集常去醫院與病歷號。

貼紙與桌布的圖由前端依 `code`、`qr_url` 產生。

## 救護人員查詢（由 responder 模組呼叫）

`lookup_for_responder(responder, code, method, latitude, longitude)`：

1. 用有效卡號找到救命卡，找不到回 `404 CARD_NOT_FOUND`
2. 寫查看紀錄（救護人員姓名、分隊、人員編號存快照）
3. 回傳 `ResponderCardOut`（UI R03，只有必要欄位）：姓名、年齡、性別、血型、緊急聯絡人（撥號）、慢性病、過敏、目前用藥、免責文字、`close_at`（30 分鐘後）
4. 紀錄寫入後，推播所有綁定家屬（UI F07）：「救護人員查看了王美玉的緊急醫療卡｜11/07 14:32｜臺北市政府消防局 大安分隊｜人員編號 A12345。長輩可能需要緊急協助，請盡快聯絡。」，`data.call` 為撥給長輩的 `phone_call` 訊息。推播失敗不影響救護人員查看

## 提供給其他模組

- `elder_profile(elder_id)`：姓名與性別（推播給家屬：「王美玉 中午 12:00 該吃藥了」「記得關心她」）

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

- `emergency_cards`：姓名、慢性病、過敏加密儲存
- `emergency_contacts`：一位；姓名、電話加密儲存
- `card_codes`：卡號紀錄，每張卡只有一組有效
- `card_access_logs`：查看紀錄，只能新增
- `consents`：同意紀錄（同意者、時間、撤回時間）

## 依賴

- `family`：權限、要通知的家人與稱呼
- `medication`：正在吃的藥
- `notification`：推播
- `integrations/townpass`：`PhoneCallMessage`
