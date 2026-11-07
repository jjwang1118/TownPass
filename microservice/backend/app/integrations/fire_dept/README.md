# app/integrations/fire_dept/

臺北市政府消防局人員名冊的介面，用於確認救護人員在職且有救護權限。

| 檔案 | 內容 |
|---|---|
| `client.py` | `RosterEntry`（姓名、單位、職稱、是否在職、是否有救護權限）、`FireDeptRoster` 介面 |

- **比賽時**：`responder` 模組直接讀 `responders` 表的 3 筆模擬帳號（A12345、A23456 在職；A34567 已離職），由 `seed/` 匯入；登入畫面的分隊清單在 `responder/rules.py`（範例名稱）。
- **正式版**：實作 `FireDeptRoster` 查詢消防局，`responder` 模組不用改。

狀態：只有介面。
