### CM-CRD-03 下次回診卡

> 來源：Figma「藥報平安」→ `E02｜長者：首頁` → `下次回診卡`（node `9:1627`）

| 項目 | 內容 |
| --- | --- |
| **Component ID** | `CM-CRD-03` |
| **名稱** | 下次回診卡 |
| **類型** | Card（可點） |
| **使用於** | 長者：`EL-PG-01`／家屬：`FM-PG-03`（家屬首頁） |
| **可見身分／切換** | 長者、家屬皆可見；標籤文字依身分不同：長者看到「下次回診」，家屬看到「長輩的下次回診」，其餘內容相同 |
| **狀態／變體** | 無 |
| **互動** | 點擊整張卡 → 進入回診詳情 |
| **限制** | 僅在已有預約時顯示，無預約時整塊隱藏 |

**結構與資料**

| 子元素 | 內容／資料欄位 | 範例 |
| --- | --- | --- |
| 標籤 | 固定文字（依身分） | 長者：下次回診／家屬：長輩的下次回診 |
| 日期時間 | `appointment.datetime` | 11/14（五）09:30 |
| 院區｜科別｜醫師 | `appointment.hospital`｜`appointment.department`｜`appointment.doctor` | 仁愛院區｜心臟科｜林醫師 |

**設計／排版規格**

| 部位 | 尺寸 | 間距 | 圓角 | 顏色 token | 字級／字重 | 對齊 |
| --- | --- | --- | --- | --- | --- | --- |
| 容器 | 寬 343、依內容高 | padding 16、gap 4 | 12 | 底 `background-color-White/50` #FFFFFF；框 `color-Grey/200` #CAD1D5 | — | 垂直排列 |
| └ 標籤 | 依內容 | — | — | `text-second-color-Gray/700` #475259 | `font-H3-semibold` 16/22 Bold | 置左 |
| └ 日期時間 | 依內容 | — | — | `text-primary-color-Gray/800` #30383D | `font-H2-semibold` 24/32 Bold | 置左 |
| └ 院區｜科別｜醫師 | 依內容 | — | — | `text-primary-color-Gray/800` #30383D | `font-H3-regular` 16/22 | 置左 |
