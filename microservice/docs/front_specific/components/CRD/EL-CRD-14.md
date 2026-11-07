### EL-CRD-14 藥單列

> 來源：Figma「藥報平安」→ `E08｜長者：我的藥單` → `藥單-A`／`藥單-B`／`藥單-已吃完`（node `10:2425`／`10:2433`／`10:2442`）

| 項目 | 內容 |
| --- | --- |
| **Component ID** | `EL-CRD-14` |
| **名稱** | 藥單列 |
| **類型** | Card（可點） |
| **使用於** | `EL-PG-18` |
| **狀態／變體** | 吃藥中（白底，可點）／已吃完（灰底，徽章灰色「舊」字，仍可點查看內容） |
| **互動** | 點擊整列 → 進入該藥單詳情（顯示此藥單所有藥品，ID 待定） |

**結構與資料**

| 子元素 | 內容／資料欄位 | 範例 |
| --- | --- | --- |
| 藥單徽章 | `rx.code`（A／B／C...，已吃完顯示「舊」） | A |
| 院區｜科別 | `rx.hospital`｜`rx.department` | 仁愛院區｜心臟科 |
| 看診日期｜狀態 | `rx.visitDate`｜`rx.daysLeft` 或「已吃完」 | 11/05 看診｜還剩 26 天 |
| 展開箭頭 | 固定圖示 | — |

**設計／排版規格**

| 部位 | 尺寸 | 間距 | 圓角 | 顏色 token | 字級／字重 | 對齊 |
| --- | --- | --- | --- | --- | --- | --- |
| 容器 | 寬 343、依內容高 | padding 16、gap 12 | 12 | 見下方「依狀態」表 | — | 水平排列、置中 |
| └ 藥單徽章 | 64×48 | padding 左右 14 | 24 | 見下方「依狀態」表 | `font-H2-semibold` 24/32 Bold | 置中 |
| └ 院區｜科別 | 依內容 | gap 2 | — | 見下方「依狀態」表 | `font-H3-semibold` 16/22 Bold | 置左 |
| └ 看診日期｜狀態 | 依內容 | — | — | 見下方「依狀態」表 | `font-H3-regular` 16/22 | 置左 |
| └ 展開箭頭 | 24×24 | — | — | — | — | 置中 |

**依狀態**（只列會變的屬性）

| 狀態 | 容器底色 | 容器框線 | 徽章底色 | 徽章文字色 | 文字色 |
| --- | --- | --- | --- | --- | --- |
| 吃藥中（A 系列） | `background-color-White/50` #FFFFFF | `color-Grey/200` #CAD1D5 | `color-Primary/700` #356C77 | `color-White/50` #FFFFFF | `text-primary-color-Gray/800` #30383D／`text-second-color-Gray/700` #475259 |
| 吃藥中（B 系列） | `background-color-White/50` #FFFFFF | `color-Grey/200` #CAD1D5 | `color-Secondary/500` #F5BA4B | `text-primary-color-Gray/800` #30383D | `text-primary-color-Gray/800` #30383D／`text-second-color-Gray/700` #475259 |
| 已吃完 | `color-Grey/50` #F1F3F4 | `color-Grey/200` #CAD1D5 | `color-Grey/500` #738995 | `color-White/50` #FFFFFF | `text-second-color-Gray/700` #475259（全部文字） |
