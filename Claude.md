# TownPass

## 專案說明

**題目：要報平安**

在這個專案中，主要是針對 `65 歲以上`長者作為主要族群，以`公有醫院`的就醫與領藥為使用情境，基於台北通建立微服務。我們的微服務提供`掃描 QR Code`，將裡面的藥單轉換成表格，也支援台語語音記錄。並設置吃藥提醒服務，顯示吃藥時間，並做 TTS，同時推播給透過`邀請碼`綁定的家屬或照顧者。另外會顯示`緊急醫療卡`，在緊急時提供救護人員必要的醫療資訊。

### 功能

| 分頁 | 功能 | 說明 |
| --- | --- | --- |
| Bottom 1 | 領藥紀錄 | 掃描 QR Code 或使用台語語音，記錄領藥資訊 |
| Bottom 1 | 吃藥提醒 | 於 9:00、12:00、18:00、22:00 提醒長者，並推播給透過邀請碼綁定的人 |
| Bottom 2 | 緊急醫療卡 | 由使用者手動輸入；救護人員需輸入後才能查看，其他情況僅綁定人員可查看 |
| Bottom 3 | 回診預約（Bonus） | 限聯合醫院，依序選擇科別、醫師、星期、時段，再確認預約 |


## 互動原則

* 先詢問再動手：修改前先向使用者說明並取得確認。
* 最小修改原則：只修改需要調整的部分，不順手改動其他內容。
* 記錄修改：每個 Agent 調整後，都須依「Agent說明」中的格式，將紀錄寫入 `logs/`。

## Agent說明

在每個 session 開始時，請先詢問使用者並確認本次擔任的角色（前端工程師或後端工程師），再依該角色的說明與注意事項工作。

### 前端工程師

- **架構**：微服務是部署在外部網址的一般網頁，城市通（Flutter）依 `destinationUrl` 以 WebView 載入，屬於 Hybrid 架構。
- **App 溝通**
  - 透過 `window.flutterObject` 收發訊息，格式為 `{ name, data }`，雙向都是 JSON 字串（送出前先 `JSON.stringify`，收到後 `JSON.parse(event.data)`）。
  - 用完要 `removeEventListener`，避免重複觸發。
  - 一般瀏覽器沒有 `flutterObject`，要先判斷是否存在，必要時改用模擬資料；雙向溝通只能在 App 內測試。
  - 官方 Vue 範例：`useConnectionMessage.ts`、`useHandleConnectionData.ts`。
- **App 能力**
  - 內建（傳對應的 `name` 即可）：定位、QR Code 掃描、手機通知、裝置資訊、撥電話與 1999、開地圖與連結。
  - 自行擴充（音訊等）：選 MIT／BSD／Apache 授權的開源免費套件，繼承 `TPWebMessageHandler` 並加入 `_cachedMessageHandlers`，再設定 `Info.plist` 與 `AndroidManifest` 權限。`name` 不可與內建名稱重複。
- **WebView 注意事項**
  - 切換頁面或 App 進入背景時，要釋放 WebView 資源。
  - 彈出視窗在 iOS 預設會被阻擋，Android 需自行處理，兩個平台都要完整測試。
  - 開發時可用裝置模擬檢視，完成後必須在 App 內實測。
- **服務註冊**
  - 在 `lib/page/city_service/model/my_service_model.dart` 的 `MyServiceItemId` 新增 id，並在 `MyServiceIdExt` 的 switch 新增 case。
  - 圖示使用 SVG，放在 `assets/svg/`，檔名用 snake_case，新增後重跑 build_runner，以 `Assets.svg.xxx.svg()` 取用。
  - 熱門服務設定在 `model/trending_service_model.dart`。
- **設計規範**
  - 優先使用 Town Pass UI Kit（Figma），讓風格與城市通一致。
  - 色票：Primary `#5AB4C5`、Secondary `#F5BA4B`、Grayscale `#738995`（皆為 500 基準色）；網頁端設定於 `tailwind.config.js` 或 CSS 變數。
  - 字體：中文 PingFang TC，英數 Roboto。
  - 字級：h1 36、h2 24、title 18、h3 16、body 14、caption 12。
- **無障礙（長者為主要族群，須優先遵守）**
  - 觸控目標至少 48dp × 48dp。
  - 文字放大 200% 仍可閱讀。
  - 圖示要可朗讀，裝飾圖要隱藏；通知與 Dialog 要能被朗讀。
  - 焦點順序由上至下、由左至右；內容順序合乎邏輯，導覽順序與圖示保持一致。
  - 表單欄位標籤要清楚，鍵盤要對應輸入格式；連結描述要明確。
  - 不使用閃爍內容；每頁一個 AppBar 標題。
- **測試資料**：比賽時無法串接真實帳號，使用 `assets/mock_data/`；要展示長者情境時，修改 `account.json` 的 `birthday`、`citizen`。


### 後端工程師

### 任意 Agent

每次修改檔案後，請將紀錄附加至 `logs/{MMDD}_communication`，格式如下：

```
[Agent name]: {前端 / 後端 / other 工程師}
[Modified Description]:
- {調整重點，以列點敘述}
[Modified Time]: {MMDDHHMMSS}
[Modified Position]: {File name:Line}
```