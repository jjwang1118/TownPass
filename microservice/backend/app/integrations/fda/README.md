# app/integrations/fda/

食藥署「藥品許可證」開放資料（data.fda.gov.tw），用於同成分檢查：新增藥品時，比對它和長輩其他藥品的主成分。

| 檔案 | 內容 |
|---|---|
| `importer.py` | `import_licenses()`：把許可證資料匯入 `drug_licenses` 表 |

- **比賽時**：只匯入範例藥品需要的幾筆。
- 資料來源要列在繳交的「資料來源清單」。

狀態：只有介面。
