### CM-CRD-02 時段格

> 來源：Figma「藥報平安」→ `E02｜長者：首頁` → `時段格`（node `9:1598`，子元件 `SlotCard` node `8:1376`/`8:1383`/`8:1390`）

| 項目 | 內容 |
| --- | --- |
| **Component ID** | `CM-CRD-02` |
| **名稱** | 時段格 |
| **類型** | Card（可點） |
| **使用於** | 長者：`EL-PG-01`／家屬：`FM-PG-03`（家屬首頁） |
| **可見身分／切換** | 長者、家屬皆可見，樣式與資料完全相同（顯示同一位長輩當天的用藥時段）；家屬綁定多位長輩時，切換長輩後本元件資料跟著切換 |
| **狀態／變體** | 已過／現在／等一下 |
| **互動** | 點擊 → 進入該時段用藥詳情 |

**結構與資料**

| 子元素 | 內容／資料欄位 | 範例 |
| --- | --- | --- |
| 時段名稱 | `slot.name` | 早上／中午／晚上／睡前 |
| 時間 | `slot.time` | 09:00 |
| 藥單徽章清單 | `slot.medicineCodes` | A1　A2　B1 |
| 狀態標籤 | `slot.status` | 已過／現在／等一下（「現在」無獨立文字標籤，僅以顏色＋狀態標籤呈現） |

**設計／排版規格**（容器與共用結構）

| 部位 | 尺寸 | 間距 | 圓角 | 顏色 token | 字級／字重 | 對齊 |
| --- | --- | --- | --- | --- | --- | --- |
| 容器 | 寬 165、依內容高 | padding 12、gap 6 | 12 | 見下方「依狀態」表 | — | 垂直排列 |
| └ 時段名稱／狀態標籤列 | 寬 100% | 左右對齊（space-between） | — | 見下方「依狀態」表 | `font-H3-semibold` 16/22 Bold | 左右對齊 |
| └ 時間 | 依內容 | — | — | 見下方「依狀態」表 | `font-H2-semibold` 24/32 Bold | 置左 |
| └ 藥單徽章清單 | 寬 100% | — | — | `text-second-color-Gray/700` #475259 | `font-H3-regular` 16/22 | 置左 |

**依狀態**（只列會變的屬性）

| 狀態 | 容器底色 | 容器框線 | 狀態標籤底色 | 狀態標籤文字色 | 時段名稱／時間文字色 |
| --- | --- | --- | --- | --- | --- |
| 已過 | `color-Grey/50` #F1F3F4 | 1px `color-Grey/200` #CAD1D5 | `color-Grey/100` #E3E7E9 | `text-second-color-Gray/700` #475259 | `text-second-color-Gray/700` #475259 |
| 現在 | `color-Primary/50` #EDF8FA | 2px `color-Primary/500` #5AB4C5 | `color-Primary/500` #5AB4C5 | `color-White/50` #FFFFFF | `text-primary-color-Gray/800` #30383D |
| 等一下 | `background-color-White/50` #FFFFFF | 1px `color-Grey/200` #CAD1D5 | `color-Grey/100` #E3E7E9 | `text-second-color-Gray/700` #475259 | `text-primary-color-Gray/800` #30383D |
