# app/integrations/

外部系統的介面。service 透過這裡呼叫外部系統，不直接發 HTTP 或讀外部檔案；比賽時接模擬資料，正式上線時只換這裡的實作，service 不用改。

| 目錄 | 外部系統 | 比賽時 | 狀態 |
|---|---|---|---|
| [townpass/](townpass/) | 城市通 App 的 `{ name, data }` 訊息 | 前端轉送 App 的回覆 | ✅ 完成 |
| [tpech/](tpech/) | 北市聯醫掛號系統 | 讀資料庫的模擬門診 | 只有介面 |
| [fire_dept/](fire_dept/) | 消防局人員名冊 | 讀 `responders` 表 | 只有介面 |
| [fda/](fda/) | 藥品資料（健保用藥品項），用於同成分檢查 | 匯入全部 4.5 萬筆 | ✅ 完成 |
| [fcm/](fcm/) | Firebase Cloud Messaging 推播 | 沒有憑證時只寫 log | ✅ 完成 |

## 新增外部系統

1. 新增目錄，用 `typing.Protocol` 定義介面。
2. 寫一個模擬實作，比賽時使用。
3. 用環境變數決定使用模擬或正式實作（參考 `fcm/client.py` 的 `get_pusher()`）。
