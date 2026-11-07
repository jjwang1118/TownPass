### EL-CRD-09 藥品核對卡

> 來源：Figma「藥報平安」→ `E06｜長者：確認藥單（核對中）` → `藥品卡-A1`/`A2`/`A3`（node `10:1925`／`10:1968`／`10:2018`）
> 註：已依討論調整——所有卡片統一樣式（Figma 原稿 A2 有紅框「不確定」變體與外部「改成...」建議按鈕，已移除），卡片內改為固定的「編輯」按鈕。

| 項目 | 內容 |
| --- | --- |
| **Component ID** | `EL-CRD-09` |
| **名稱** | 藥品核對卡 |
| **類型** | Card（可點） |
| **使用於** | `EL-PG-07`、`EL-PG-08` |
| **狀態／變體** | 無（所有項目統一樣式，不再區分辨識信心） |
| **互動** | 點擊卡片本身或卡內「編輯」按鈕 → 開啟修改藥品頁（ID 待定，Figma：E06b）；點擊單顆朗讀 → 觸發 TTS，不冒泡 |

**結構與資料**

| 子元素 | 內容／資料欄位 | 範例 |
| --- | --- | --- |
| 藥單徽章 | `medicine.code` | A1 |
| 顆數 | `medicine.amount` | 1 顆 |
| 藥名＋劑量 | `medicine.name` | Amlodipine 5 毫克 |
| 功效｜服用時機 | `medicine.effect`｜`medicine.timing`（`timing` 固定為「早上／中午／晚上／睡前」四選一） | 降血壓｜早上 |
| 單顆朗讀按鈕 | 固定圖示（喇叭） | — |
| 編輯按鈕 | 固定圖示／文字（卡片內） | 編輯 |

**設計／排版規格**

| 部位 | 尺寸 | 間距 | 圓角 | 顏色 token | 字級／字重 | 對齊 |
| --- | --- | --- | --- | --- | --- | --- |
| 容器 | 寬 343、依內容高 | padding 16 | 12 | 底 `background-color-White/50` #FFFFFF；框 `color-Grey/200` #CAD1D5 | — | 垂直排列 |
| └ 藥單徽章 | 64×48 | padding 左右 14 | 24 | 底 `color-Primary/700` #356C77 | `font-H2-semibold` 24/32 Bold，色 `color-White/50` #FFFFFF | 置中 |
| └ 顆數 | 依內容 | gap 12（與徽章） | — | `text-primary-color-Gray/800` #30383D | `font-H2-semibold` 24/32 Bold | 置左 |
| └ 藥名＋劑量 | 依內容 | gap 2 | — | `text-primary-color-Gray/800` #30383D | `font-H3-regular` 16/22 | 置左 |
| └ 功效｜服用時機 | 依內容 | gap 2 | — | `text-second-color-Gray/700` #475259 | `font-H3-regular` 16/22 | 置左 |
| └ 單顆朗讀按鈕 | 48×48 | — | 24 | 底 `color-Primary/50` #EDF8FA | — | 置中 |
| └ 編輯按鈕 | 依內容（圖示＋文字或純圖示，待設計師補版面） | gap 12（與主要列） | — | `color-Primary/700` #356C77 | `font-H3-semibold` 16/22 Bold | 置右 |
