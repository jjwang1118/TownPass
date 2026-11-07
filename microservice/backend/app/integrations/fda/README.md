# app/integrations/fda/

食藥署「藥品許可證」開放資料（data.fda.gov.tw），用於同成分檢查：新增藥品時，比對它和長輩其他藥品的主成分。

| 檔案 | 內容 |
|---|---|
| `importer.py` | `import_licenses()`：新增或更新 `drug_licenses`，可重複執行 |

- **比賽時**：只匯入 `seed/data/drug_licenses.json` 的範例（字號 `DEMO-` 開頭），由 `uv run python -m seed.load` 執行。
- 資料來源要列在繳交的「資料來源清單」。

狀態：✅ 完成。
