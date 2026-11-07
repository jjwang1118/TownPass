# app/integrations/tpech/

臺北市立聯合醫院（TPECH）掛號系統的介面。

| 檔案 | 內容 |
|---|---|
| `client.py` | `TpechClient` 介面：查門診、預約、取消 |

- **比賽時**：院區、科別、醫師、門診都是 `seed/` 匯入資料庫的模擬資料，`appointment` 模組直接讀這些表。
- **正式版**：實作 `TpechClient` 串接聯醫，`appointment` 模組不用改。
- **下一期**：「帶入聯醫用藥」也會放在這裡。

狀態：只有介面。
