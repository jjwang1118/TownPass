# emergency_card — 救命卡

長輩的醫療資訊、隨機卡號、救護人員查看紀錄、健康資料同意。規格書 §5.4、§8.2。

**狀態**：待實作（API 回 501）；`rules.py` 與常見選項已完成。

## API

| 方法 | 路徑 | 說明 |
|---|---|---|
| GET | `/emergency-card/common-items` | 常見慢性病、過敏選項 ✅ |
| POST | `/elders/{elder_id}/consents` | 同意儲存健康資料（寫入救命卡前必須） |
| DELETE | `/elders/{elder_id}/consents/{type}` | 撤回同意：清空病史、過敏，卡號失效 |
| GET | `/elders/{elder_id}/emergency-card` | 長輩、家人檢視 |
| PUT | `/elders/{elder_id}/emergency-card` | 編輯 |
| PUT | `/elders/{elder_id}/emergency-card/contacts` | 緊急聯絡人（最多 2 位），回應附 `phone_call` 訊息 |
| POST | `/elders/{elder_id}/emergency-card/regenerate-code` | 重新產生卡號，舊卡號立即失效 |

## 檔案

- `rules.py`：產生卡號（`TPE-XXXX-XXXX`）、卡號正規化、QR 網址、從 QR 網址取出卡號、免責文字

## 資料表

- `emergency_cards`：慢性病、過敏加密儲存
- `emergency_contacts`：姓名、電話加密儲存
- `card_codes`：卡號紀錄，每張卡只有一組有效
- `card_access_logs`：查看紀錄，只能新增
- `consents`：同意紀錄

## 提供給其他模組

- `lookup_for_responder()`：給 `responder` 模組呼叫；寫查看紀錄並通知家人

## 依賴

- `medication`：正在吃的藥
- `family`：權限、要通知的家人
- `notification`：推播
