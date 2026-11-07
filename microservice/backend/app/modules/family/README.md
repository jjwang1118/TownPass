# family — 家人綁定與權限

長輩產生邀請碼，家人輸入或掃 QR 後綁定。也負責**所有長輩資料的權限檢查**。規格書 §3。

**狀態**：✅ 完成（測試：`tests/test_family.py`）

## API

| 方法 | 路徑 | 誰可以用 | 說明 |
|---|---|---|---|
| POST | `/family/invites` | 長輩 | 產生 6 位數邀請碼與 QR 內容（10 分鐘、只能用一次）；舊的有效邀請碼立即失效 |
| POST | `/family/bindings` | 家人 | `qr`（App 的 `qr_code_scan` 回覆）或 `code` 擇一，加上稱呼 `relation_label`（如「媽媽」） |
| GET | `/family/bindings` | 長輩、家人 | 自己的綁定清單（附 `elder_phone`，家屬「打電話給長輩」用） |
| PATCH | `/family/bindings/{id}` | 該家人 | 修改稱呼（前端存家屬和長輩的關係，例如「女兒」）；`notify_on_ack` 目前未使用（吃藥提醒已改為家屬每次同時收到） |
| POST | `/family/bindings/{id}/complete-setup` | 該家人 | 完成初始設定，之後唯讀；重複呼叫不會出錯 |
| DELETE | `/family/bindings/{id}` | 該長輩 | 解除綁定 |

邀請 QR 的內容是 `{FRONTEND_BASE_URL}/invite/{code}`，家人用一般相機掃到也會開啟前端的綁定頁。

## 錯誤

| code | HTTP | 情況 |
|---|---|---|
| `ROLE_REQUIRED` | 403 | 還沒選擇身分 |
| `ELDER_ONLY` / `FAMILY_ONLY` | 403 | 身分不符（家人產生邀請碼、長輩輸入邀請碼） |
| `INVITE_INVALID` | 400 | 邀請碼格式不正確 |
| `INVITE_NOT_FOUND` | 404 | 找不到邀請碼 |
| `INVITE_USED` | 409 | 已經使用過 |
| `INVITE_EXPIRED` | 409 | 已過期，或長輩產生了新的邀請碼 |
| `ALREADY_BOUND` | 409 | 已經綁定這位長輩；邀請碼不會被用掉 |
| `BINDING_NOT_FOUND` | 404 | 綁定不存在或已解除 |

## 資料表

- `family_invites`：邀請碼、到期時間、使用時間
- `family_bindings`：長輩、家人、稱呼、`notify_on_ack`、`setup_completed_at`、`revoked_at`

## 檔案

- `rules.py`：產生邀請碼、邀請 QR 網址、從輸入或 QR 取出邀請碼

## 提供給其他模組

**`ensure_access(user_id, elder_id, Access.READ | Access.WRITE)`**：存取長輩資料前都要呼叫，沒有權限時丟 `Forbidden`。

| 呼叫者 | READ | WRITE |
|---|---|---|
| 長輩本人（身分為長輩） | ✅ | ✅ |
| 已綁定、尚未完成初始設定的家人 | ✅ | ✅ |
| 已綁定、已完成初始設定的家人 | ✅ | ❌ `READ_ONLY` |
| 沒綁定或已解除 | ❌ `NOT_BOUND` | ❌ `NOT_BOUND` |

**`list_family_ids(elder_id, ack_subscribers_only=False)`**：要通知的家人。`ack_subscribers_only=True` 時只回傳有開啟「長輩回應通知」的家人。

**`list_family_members(elder_id)`**：家人與他們對長輩的稱呼（如「媽媽」）、是否開啟回應通知，用於組通知文字。

## 依賴

- `auth`：`get_me()`、`get_profiles()` 查身分與姓名
