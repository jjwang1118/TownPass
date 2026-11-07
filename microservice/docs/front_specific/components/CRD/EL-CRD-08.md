### EL-CRD-08 藥單標頭

> 來源：Figma「藥報平安」→ `E06｜長者：確認藥單（核對中）` → `藥單標頭`（node `10:1885`）

| 項目 | 內容 |
| --- | --- |
| **Component ID** | `EL-CRD-08` |
| **名稱** | 藥單標頭 |
| **類型** | Card（不可點，純展示） |
| **使用於** | `EL-PG-07`、`EL-PG-08` |
| **狀態／變體** | 無 |
| **互動** | 無 |

**結構與資料**

| 子元素 | 內容／資料欄位 | 範例 |
| --- | --- | --- |
| 藥單分類字母徽章 | `prescription.code` | A |
| 院區｜科別 | `prescription.hospital`｜`prescription.department` | 仁愛院區｜心臟科 |
| 看診日期｜天數 | `prescription.visitDate`｜`prescription.days` | 看診 2026/11/05｜28 天 |

**設計／排版規格**

| 部位 | 尺寸 | 間距 | 圓角 | 顏色 token | 字級／字重 | 對齊 |
| --- | --- | --- | --- | --- | --- | --- |
| 容器 | 寬 343、依內容高 | padding 上下 12、左右 16、gap 12 | 12 | 底 `color-Grey/50` #F1F3F4 | — | 水平排列、置中 |
| └ 分類字母徽章 | 64×48 | padding 左右 14 | 24 | 底 `color-Primary/700` #356C77 | `font-H2-semibold` 24/32 Bold，色 `color-White/50` #FFFFFF | 置中 |
| └ 院區｜科別 | 依內容 | gap 2（與下一行） | — | `text-primary-color-Gray/800` #30383D | `font-H3-semibold` 16/22 Bold | 置左 |
| └ 看診日期｜天數 | 依內容 | — | — | `text-second-color-Gray/700` #475259 | `font-H3-regular` 16/22 | 置左 |
