# 「要報平安」前端規格

## 技術選型

| 項目 | 決定 |
| --- | --- |
| 開發語言 | TypeScript |
| 前端框架 | Vue 3 |

## 編號規則

ID 格式：`{使用者}-{類型}-{流水號}`，介面與元件共用此規則。

**使用者前綴**（誰看得到）

| 前綴 | 使用者 |
| --- | --- |
| `EL` | 長者 |
| `FM` | 家人 |
| `RE` | 救護人員 |
| `CM` | 共用（多種身分皆可見） |

**類型前綴**

| 介面類型 | 說明 | 元件類型 | 說明 |
| --- | --- | --- | --- |
| `PG` | 完整頁面 | `SYS` | 系統元件（status bar、home indicator） |
| `MD` | 彈窗 | `NAV` | 導覽列 |
| `SH` | 底部抽屜 | `BTN` | 按鈕 |
| | | `SEG` | 分段切換 |
| | | `TAG` | 標籤 |
| | | `CRD` | 卡片 |
| | | `CHK` | 勾選框 |
| | | `ALT` | 提醒框 |
| | | `TXT` | 文字區塊 |
| | | `SEL` | 下拉選單 |
| | | `INP` | 文字輸入框 |
| | | `STP` | 數量選擇器 |

> 介面表中的元件一律以 Component ID 引用，元件規格只在「元件規格」章節定義一次。

## 規格表撰寫範本

每個畫面寫成「一張介面表」，畫面上的元件各寫成「一張元件表」，介面表裡只用 Component ID 引用元件。同一個元件被多個畫面使用時，元件表只寫一次，在「使用於」列出所有畫面。

### 介面表：欄位說明

| 欄位 | 必填 | 怎麼寫 | 範例 |
| --- | --- | --- | --- |
| **Interface name** | ✔ | 畫面的中文名稱，和 Figma frame 名稱一致 | 長者首頁 |
| **Interface ID** | ✔ | `{使用者}-{類型}-{流水號}`，括號註明 Figma 編號 | `EL-PG-01`（Figma：E02） |
| **Pre-interface** | ✔ | 列出**所有**入口，一行一個：`來源 ID` + 名稱 → 點擊什麼／什麼條件 | `CM-PG-01` 選擇身分 → 點擊「我是長者」 |
| **畫面尺寸** | ✔ | 畫面寬 × 高、頁面底色 token；可捲動要註明 | 375 × 812；底色 `background-color-White/50` #FFFFFF |
| **版面結構** | ✔ | 由上到下編號，每一項 → 元件 ID；子層用「└」或 3.1、3.2 | 3.2 下一次吃藥 → `EL-CRD-03` |
| **內容區排版** | ✔ | padding（上下左右）、gap、內容寬度、排列方向、捲動方向 | padding 上 16、下 24、左右 16；gap 16 |
| **顯示資料** | | 畫面上會變動的資料，寫範例值 | 長者姓名：王美玉 |
| **規則** | | 顯示條件、狀態計算、按鈕何時可點、展示用限制 | 全部勾選後「加入」才可點 |
| **Next interface** | ✔ | 每個可點的東西一行：點擊什麼 → `目標 ID`；還沒畫的頁面寫「（ID 待定）」 | 點擊「我的藥單」→ 我的藥單（ID 待定） |

### 元件表：欄位說明

**① 基本資訊**

| 欄位 | 必填 | 怎麼寫 | 範例 |
| --- | --- | --- | --- |
| **Component ID** | ✔ | `{使用者}-{類型}-{流水號}` | `EL-CRD-04` |
| **名稱** | ✔ | 元件中文名稱 | 時段卡 |
| **類型** | ✔ | 元件類型＋能不能點；用到官方元件要寫官方名稱 | Card（可點）／Button（TownPass 官方 `button`） |
| **使用於** | ✔ | 所有用到它的 Interface ID | `EL-PG-01`、`EL-PG-03` |
| **狀態／變體** | | 列出所有狀態或變體 | 已過／現在／等一下 |
| **互動** | | 點擊後發生什麼 | 點擊 → 依語言朗讀 |
| **限制** | | 展示用、正式版移除等 | 僅供比賽展示 |

**② 結構與資料**

| 子元素 | 內容／資料欄位 | 範例 |
| --- | --- | --- |
| 子元素名稱（和 Figma layer 名一致） | 固定文字，或資料欄位 `object.field` | 實際顯示的值 |

**③ 設計／排版規格**（數值一律從 Figma 讀，不估算）

| 部位 | 尺寸 | 間距 | 圓角 | 顏色 token | 字級／字重 | 對齊 |
| --- | --- | --- | --- | --- | --- | --- |
| 第一列寫容器本身，之後每個子元素一列，子層用「└」 | 寬 × 高；依內容變動要寫「依內容」 | padding、gap | px | `token 名稱` + #HEX；底、框、字分開寫 | `font-xxx` 字級/行高 字重 | 排列方向、對齊方式 |

> 有多種狀態時，另外加一張「依狀態」表，只列會變的屬性（參考 `EL-CRD-04`）。

### 空白框架（複製後填寫）

````markdown
### {Interface ID} {Interface name}

> 來源：Figma「{檔案名}」→ `{frame 名稱}`（node `{node-id}`）

| 項目 | 內容 |
| --- | --- |
| **Interface name** | |
| **Interface ID** | `XX-XX-00`（Figma：） |
| **Pre-interface** | • `XX-XX-00` {名稱} → 點擊「」 |
| **畫面尺寸** | 375 × 812；底色 `` |
| **版面結構**<br>（由上到下） | 1. → `XX-XXX-00`<br>2. → `XX-XXX-00` |
| **內容區排版** | • padding：上 、下 、左右 <br>• gap：<br>• 內容寬度： |
| **顯示資料** | • |
| **規則** | • |
| **Next interface** | • 點擊「」→ `XX-XX-00` |

### {Component ID} {名稱}

| 項目 | 內容 |
| --- | --- |
| **Component ID** | `XX-XXX-00` |
| **名稱** | |
| **類型** | |
| **使用於** | `XX-XX-00` |
| **狀態／變體** | |
| **互動** | |

**結構與資料**

| 子元素 | 內容／資料欄位 | 範例 |
| --- | --- | --- |
| | | |

**設計／排版規格**

| 部位 | 尺寸 | 間距 | 圓角 | 顏色 token | 字級／字重 | 對齊 |
| --- | --- | --- | --- | --- | --- | --- |
| 容器 | | | | | | |
| └ 子元素 | | | | | | |
````

## 串接後端

前端所有資料都來自後端 API（`microservice/backend`，規格書 `docs/backend-spec.md` §7）：

| 檔案 | 內容 |
| --- | --- |
| `src/api/client.ts` | 呼叫 API：網址、登入憑證、錯誤（`ApiError` 的 `message` 可直接顯示） |
| `src/api/types.ts` | 後端回應格式 |
| `src/api/mappers.ts` | 後端資料 ↔ 前端型別（畫面元件只用 `@/types`） |
| `src/store/index.ts` | 後端資料的快取與各動作；只有草稿、預約選擇、朗讀語言等畫面暫存存在 localStorage |

- **後端網址**：環境變數 `VITE_API_BASE`；沒有設定時用「目前網頁的主機:8000」，所以電腦瀏覽器（localhost:5173）連 `localhost:8000`，模擬器（10.0.2.2:5173）連 `10.0.2.2:8000`。
- **登入**：長者、家屬在台北通 App 內用 `userinfo` 登入；一般瀏覽器沒有 App 時用模擬帳號（長者「王美玉」、家屬「陳小華」）。救護人員用分隊＋人員編號＋密碼（範例帳號見 `backend/seed/README.md`）。
- **連不到後端**時畫面上方顯示紅色提示與「重新連線」按鈕。
- **救護人員查詢**：不使用身分證字號，改輸入救命卡卡號（長者的緊急醫療卡頁會顯示卡號），App 內也可以掃卡片 QR Code。
- **緊急醫療卡**：依 UI 只有一位緊急聯絡人，不收集常去醫院與病歷號。
- **拍藥袋**：手機上用 Tesseract 辨識藥袋照片上的字，送後端 `ocr-preview` 整理成藥單，見下一節。

本機測試：後端 `docker compose --profile app up -d --build`（或 `uv run uvicorn app.main:app --reload`），前端 `npm install && npm run dev`，瀏覽器開 <http://localhost:5173>。

## 拍藥袋 OCR

```
拍藥袋頁（EL-PG-05）拍照或選照片 ─▶ src/services/bagOcr.ts：tesseract.js 在手機上辨識每一行字
  ─▶ store.startDraftFromOcr(lines)：POST …/prescriptions/ocr-preview { name: 'ocr_scan', data: { lines } }
  ─▶ 後端用規則整理成藥單、比對健保藥品資料、打信心分數 ─▶ 確認藥單（EL-PG-07，看錯的欄位紅框）
```

- **推論在裝置端、不連外網**：tesseract.js 以 WebAssembly 在 WebView（或瀏覽器）裡執行；worker、核心、字庫由 `scripts/copy-tesseract.mjs` 在 `npm run dev`／`npm run build` 前從 `node_modules` 複製到 `public/tesseract/`（已加入 .gitignore），和前端一起部署，不向 CDN 下載。關閉網路仍可辨識（照片也不會上傳，只送辨識出的文字）。
- **不需要修改 App**：照片用 `<input type="file">` 取得（「拍藥袋照片」開相機、「從相簿選照片」開相簿），和掃 QR 頁相同。
- **設定**：繁中＋英文、只用 LSTM、版面模式 `SINGLE_BLOCK`（藥袋是一行一行的字；實測比自動版面分析準，自動模式常漏掉每行第一個字）、保留大空白；照片長邊先縮到 2000 像素。
- **資源釋放**：進入拍藥袋頁先在背景載入引擎，離開時 `releaseBagOcr()` 釋放（WebView 注意事項）。
- **大小**：手機只下載一份核心（約 3.8 MB，依是否支援 SIMD 自動挑）與兩個字庫（約 4.5 MB），之後由瀏覽器快取。
- **測試**：電腦瀏覽器開拍藥袋頁，用「從相簿選照片」選藥袋照片即可；模擬器的相機是假畫面，實拍請用實機。

### 模型與套件揭露（競賽須知：模型名稱、版本、量化格式、推論框架、來源）

| 項目 | 內容 |
| --- | --- |
| 模型 | Tesseract OCR LSTM 辨識模型：繁體中文 `chi_tra`、英文 `eng` |
| 版本 | tessdata `4.0.0_best_int`（npm `@tesseract.js-data/chi_tra@1.0.0`、`@tesseract.js-data/eng@1.0.0`） |
| 量化格式 | 整數量化（best_int，由 tessdata_best 轉換），gzip 壓縮的 `.traineddata` |
| 推論框架 | tesseract.js 7.0.0（Tesseract 5 編譯成 WebAssembly，tesseract.js-core 6.1.2），在手機的 WebView 執行 |
| 來源與授權 | tesseract.js、tesseract.js-core：Apache-2.0；字庫資料來自 tesseract-ocr/tessdata（Apache-2.0），npm 包裝為 MIT。Tesseract 原由 HP 開發、Google 開源，現由社群維護，非大陸廠牌 |

