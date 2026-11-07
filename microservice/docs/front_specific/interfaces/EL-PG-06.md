### EL-PG-06 長者：掃描藥袋 QR Code

> 來源：**自行設計**（非 Figma 原稿），參考 `EL-PG-05`（長者：拍藥袋，Figma node `9:2025`）版面調整而成，待設計師於正式稿確認。

| 項目 | 內容 |
| --- | --- |
| **Interface name** | 長者：掃描藥袋 QR Code |
| **Interface ID** | `EL-PG-06`（無對應 Figma frame，自行設計） |
| **Pre-interface** | • `EL-PG-04` 長者：新增藥單 → 點擊「掃描藥袋 QR Code」（`CM-CRD-04`） |
| **畫面尺寸** | 375 × 812；底色 `background-color-White/50` #FFFFFF；內容區可垂直捲動（掃描區以 flex-1 撐滿剩餘空間，一般不需捲動） |
| **版面結構**<br>（由上到下） | 1. 導覽列（返回＋標題） → `CM-NAV-02`（標題：掃描 QR Code）<br>2. 相機掃描區 → `EL-CRD-07`<br>3. 改用拍照按鈕 → `CM-BTN-03`（文字：改用拍照） |
| **內容區排版** | • padding：上 16、下 24、左右 16<br>• gap：16<br>• 內容寬度：343<br>• 垂直排列；相機掃描區 flex-1 撐滿剩餘高度 |
| **顯示資料** | 無（相機即時畫面，非資料欄位） |
| **規則** | • 掃描到有效 QR Code 後自動辨識並跳轉下一頁，不需手動按鈕<br>• 藥袋需醫院合作提供 QR Code 才能使用，若無 QR Code 或掃描失敗，提供「改用拍照」按鈕切換回 `EL-PG-05` |
| **Next interface** | • 掃描成功辨識 QR Code → `EL-PG-07` 長者：確認藥單（核對中）<br>• 點擊「改用拍照」→ `EL-PG-05`<br>• 點擊返回鍵 → 回 `EL-PG-04` |
