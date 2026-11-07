### CM-CRD-01 藥品卡

> 來源：Figma「藥報平安」→ `E02｜長者：首頁` → `藥品卡-B1`（node `9:1550`）

| 項目 | 內容 |
| --- | --- |
| **Component ID** | `CM-CRD-01` |
| **名稱** | 藥品卡 |
| **類型** | Card（可點） |
| **使用於** | 長者：`EL-PG-01`、`EL-PG-03`／家屬：`FM-PG-04`（長輩用藥詳情，用法同 `EL-PG-03`） |
| **可見身分／切換** | 長者、家屬皆可見；家屬視角下點擊整列**不會**進入編輯（家屬僅能查看，不能修改），僅長者視角可能依情境導向編輯流程 |
| **狀態／變體** | 無（本頁僅見預設樣式） |
| **互動** | 點擊「單顆朗讀」圖示 → 觸發 TTS，不冒泡至整列點擊；整列點擊行為依身分而定（見上方可見身分說明） |

**結構與資料**

| 子元素 | 內容／資料欄位 | 範例 |
| --- | --- | --- |
| 藥單徽章 | `medicine.code` | B1 |
| 顆數 | `medicine.amount` | 1 顆 |
| 藥名劑量 | `medicine.name` | Metformin 500 毫克 |
| 科別｜功效｜服用時機 | `medicine.department`｜`medicine.effect`｜`medicine.timing`（`EL-PG-01` 三項都顯示；`EL-PG-03` 科別已在頁面分類標籤顯示過，卡片只顯示 `功效｜服用時機`） | `EL-PG-01`：新陳代謝科｜降血糖｜飯後／`EL-PG-03`：降血糖｜飯後 |
| 單顆朗讀按鈕 | 固定圖示（喇叭） | — |

**設計／排版規格**

| 部位 | 尺寸 | 間距 | 圓角 | 顏色 token | 字級／字重 | 對齊 |
| --- | --- | --- | --- | --- | --- | --- |
| 容器 | 寬 343、依內容高 | padding 16 | 12 | 底 `background-color-White/50` #FFFFFF；框 `color-Grey/200` #CAD1D5 | — | 垂直排列 |
| └ 藥單徽章 | 64×48 | padding 左右 14 | 24 | 底 `color-Secondary/500` #F5BA4B | `font-H2-semibold` 24/32 Bold，色 `text-primary-color-Gray/800` #30383D | 置中 |
| └ 顆數 | 依內容 | gap 12（與徽章） | — | `text-primary-color-Gray/800` #30383D | `font-H2-semibold` 24/32 Bold | 置左 |
| └ 藥名劑量 | 依內容 | gap 2（與顆數） | — | `text-primary-color-Gray/800` #30383D | `font-H3-regular` 16/22 | 置左 |
| └ 科別｜功效｜時機 | 依內容 | gap 2 | — | `text-second-color-Gray/700` #475259 | `font-H3-regular` 16/22 | 置左 |
| └ 單顆朗讀按鈕 | 48×48 | — | 24 | 底 `color-Primary/50` #EDF8FA | — | 置中 |
