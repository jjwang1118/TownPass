# speech — 朗讀稿

把結構化資料（編號、藥名、顆數、時段…）套進各語言的模板，產生交給手機 TTS 念的文字。只有純函式，沒有 API 和資料表。

| 檔案 | 內容 |
|---|---|
| `rules.py` | 模板與念法 |
| `glossary.py` | 英文稿用的中英對照表（科別、用途、稱呼、姓氏、飯前飯後） |

**狀態**：🚧 國語（`Lang.ZH`）、英文（`Lang.EN`）完成；台語未做（測試：`tests/test_rules.py`）

## 為什麼用模板，不用翻譯

朗讀稿是後端用資料組出來的，不是使用者打的自由文字。每種語言各寫一套模板，用同一份資料直接套出來：

- 內容固定、不會翻錯，對用藥資訊很重要
- 不需要呼叫翻譯 AI，可離線（比賽規定推論要在裝置端）

## API 回傳

藥卡（`MedicationOut`）與提醒畫面（`ReminderOut`）同時回傳兩種，前端放「念中文」「Read in English」兩個按鈕各自朗讀：

| 欄位 | 語言 | 給誰 |
|---|---|---|
| `speech_text` | 國語 | 長輩、家人 |
| `speech_text_en` | 英文 | 外籍看護 |

推播內容維持國語。

## 函式

| 函式 | 用在哪裡 | 國語 | 英文 |
|---|---|---|---|
| `medication_card()` | 藥卡「念給我聽」 | 1 號藥，脈優錠，家醫科開的，降血壓。一次 1 顆，飯後吃，早上 8 點。還剩 19 天。 | Medicine number 1, Amlodipine 5mg, from Family Medicine, for blood pressure. Take 1 tablet after meals, at 8 AM. 19 days left. |
| `reminder()` | 吃藥提醒推播與提醒畫面 | 陳阿嬤，吃藥時間到囉～飯後吃：1 號 脈優錠 2 顆、3 號 Metformin 500mg 1 顆 | Grandma Chen, it's time for your medicine. After meals: number 1, Amlodipine 5mg, 2 tablets; number 3, Metformin 500mg, 1 tablet. |
| `drug_name()`、`drug_name_en()` | 決定要念的藥名 | 見下方 | 見下方 |
| `department_en()`、`purpose_en()`、`title_en()` | 英文稿的科別、用途、稱呼 | — | 家醫科 → Family Medicine；降血壓 → blood pressure；陳阿嬤 → Grandma Chen |
| `speak_time()`、`qty_text()` | 時間、顆數的念法 | 早上 7 點半、1 顆半 | 7:30 AM、1 and a half tablets |

## 藥名怎麼念

**國語稿：有中文名就只念中文名，只有英文名就照原文念。** 依序找含中文的名稱：

1. 食藥署許可證的中文品名（`drug_licenses.name_zh`，用藥品的 `license_no` 查）
2. 藥袋上的藥名（`medications.name`）
3. 都沒有中文 → 念藥袋上的原文

**英文稿：念英文名，只有中文名就不念。** 依序：藥袋上藥名的英文部分 → 許可證英文品名（`drug_licenses.name_en`）。

吃藥提醒建立時會把要念的藥名存進 `reminder_events.items[].speech_name`、`speech_name_en`，因為藥品停用後編號會被重用，之後重念同一筆提醒時藥名不會變。

## 英文稿的科別、用途、稱呼

這三個欄位是中文，英文語音念不出來，所以用 `glossary.py` 的對照表翻成原本的意思：

| 欄位 | 做法 | 查不到時 |
|---|---|---|
| 科別 | `DEPARTMENTS`（含聯醫門診資料的科別） | 原文有英文就念英文部分，否則不念 |
| 用途 | `PURPOSES`，念成「for …」 | 同上 |
| 稱呼 | `KINSHIP` 找稱謂（阿嬤 → Grandma）＋ `SURNAMES` 找姓氏（陳 → Chen）；媽媽、爸爸不加姓 | 不念稱呼，改成「It's time for your medicine.」 |

國語稿的科別、用途、稱呼仍去掉英文字母（例如「ENT 耳鼻喉科」念「耳鼻喉科」）。

要補詞彙直接加在 `glossary.py`，並在 `tests/test_rules.py` 補一個例子。

## 之後加台語

1. 在 `Lang` 加上 `NAN`，在各函式補上台語模板，修改 `_ensure_supported`
2. API 加 `speech_text_nan`（或改成依使用者偏好回傳）

手機 TTS 大多不支援台語，發音方式（預錄片段拼接或裝置端模型）之後再決定。
