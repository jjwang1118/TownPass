# app/modules/

功能模組。每個模組都用同樣的三層結構（規格書 §4）。

## 模組內的檔案

| 檔案 | 層 | 負責 | 不可以做 |
|---|---|---|---|
| `router.py` | API 層 | HTTP 路由、輸入驗證、登入檢查 | 直接存取資料庫；寫業務規則 |
| `service.py` | 業務層 | 業務規則、權限、交易（commit） | import FastAPI；丟 `HTTPException` |
| `repository.py` | 資料層 | 查詢、新增、修改資料（只 flush） | 寫業務規則；commit |
| `schemas.py` | — | Pydantic：API 的輸入與輸出 | |
| `models.py` | — | SQLAlchemy：資料表 | |
| `rules.py` | — | 沒有 I/O 的純計算，方便測試（需要時才有） | |

呼叫方向只能往下：router → service → repository。

## 模組一覽

| 模組 | 功能 | API 數 | 狀態 |
|---|---|---|---|
| [auth/](auth/) | 台北通登入、選擇身分 | 3 | ✅ 完成 |
| [family/](family/) | 邀請碼、綁定、**權限檢查** | 6 | ✅ 完成 |
| [medication/](medication/) | 藥品、掃 QR 新增、時段 | 9 | ✅ 完成 |
| [reminder/](reminder/) | 吃藥提醒、回應、通知家人、回診提醒 | 4 | ✅ 完成 |
| [emergency_card/](emergency_card/) | 救命卡、卡號、查看紀錄、同意 | 7 | ✅ 完成 |
| [responder/](responder/) | 救護人員登入、查詢救命卡 | 2 | ✅ 完成 |
| [appointment/](appointment/) | 院區、門診、預約 | 7 | 待實作 |
| [notification/](notification/) | 推播 token、發送推播 | 2 | ✅ 完成 |
| [internal/](internal/) | 排程入口 `/internal/tick` | 1 | ✅ 完成（預約提醒待加入） |
| [demo/](demo/) | 展示用觸發（只在 `DEMO_MODE`） | 3 | ✅ 完成 |

## 模組之間

只能 **service 呼叫 service**，不可以 import 別的模組的 repository。

```
family ─────────────▶ auth（身分、姓名）
medication ─────────▶ family（權限）
reminder ───────────▶ medication、family、emergency_card、auth、notification
emergency_card ─────▶ medication、family、notification
responder ──────────▶ emergency_card
appointment ────────▶ medication（上次的科別、醫師）、family
internal ───────────▶ reminder、appointment
```

存取長輩資料前，一律先呼叫 `FamilyService.ensure_access()` 檢查權限。

## 新增模組

1. 建立目錄，放入上面的檔案和 `README.md`。
2. 在 `app/models.py` 匯入新模組的 `models`。
3. 在 `app/main.py` 掛上新模組的 `router`。
4. 產生 migration（見 `alembic/README.md`）。
