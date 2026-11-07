# 台北城市微服務競賽：專案規範與內容整理

本文件整理「2026 臺北秋季程式設計節・城市通（TownPass）微服務大黑客松」的專案規範與開發內容，供隊伍賽前準備和開發時查閱。
內容包含環境建置、App 與微服務的雙向溝通、服務開發與設計規範、AI 使用規則、部署流程，以及競賽當天的繳交項目。

---

## 0. 環境建置

```bash
# 1. 取得原始碼
git clone https://github.com/taipei-doit/TownPass.git
cd TownPass

# 2. 照 .fvmrc 裝 Flutter 3.47.6
fvm install

# 3. 裝套件、產生程式碼
fvm flutter pub get
fvm dart run build_runner build --delete-conflicting-outputs

# 4. 開啟模擬器或連接手機後執行
fvm flutter run
```

**build_runner 的用途**
產生 assets.gen.dart（圖示、Mock 資料的路徑）和 JSON 序列化的程式碼。新增圖示後需重新執行。

**`--delete-conflicting-outputs`**
清除與舊產出衝突的檔案，避免建置錯誤。

> **提醒**：首次建置需要較長時間，iOS 會先下載 Swift Package，請耐心等候。

---

## 1. 檔案結構與位置

```text
TownPass/
├─ lib/
│  ├─ bean/          資料模型
│  ├─ page/          各頁面：city_service、home…
│  ├─ service/       帳號、定位、通知
│  ├─ util/          TP 元件、web_message_handler
│  └─ main.dart
├─ assets/
│  ├─ mock_data/     5 個假資料 JSON
│  ├─ svg/           108 個圖示
│  └─ image/
├─ fonts/            PingFang TC
├─ android/  ios/
└─ .fvmrc            Flutter 3.47.6
```

**常用修改位置**

| 用途 | 位置 |
| --- | --- |
| 新增服務 | `lib/page/city_service/model/my_service_model.dart` |
| 擴充 App 能力 | `lib/util/web_message_handler/` |
| 切換測試帳號 | `assets/mock_data/account.json` |

> 依 taipei-doit/TownPass main 分支（2026/10）整理

---

## 2. 使用 Mock 資料進行測試

比賽時無法串接臺北市真實的帳號系統，因此專案在 `assets/mock_data/` 放了 5 個 JSON 假資料。App 啟動時讀取這些檔案，模擬「已登入的市民」與首頁內容。

`assets/mock_data/account.json`（節錄）

```json
{
  "name": "TP_SUCCESS",
  "status": 0,
  "data": {
    "username": "Wesley",
    "realName": "金大森",
    "verifyLevel": "3",
    "addresses": [{ "city": "臺北市", … }],
    "citizen": true,
    "nativePeople": false
  }
}
```

**欄位說明**

| 欄位 | 說明 |
| --- | --- |
| `name` / `status` | `TP_SUCCESS`、`0` 表示查詢成功 |
| `username` / `realName` | 帳號名稱與真實姓名（測試用假資料） |
| `verifyLevel` | 身分驗證等級 |
| `addresses` | 地址 |
| `citizen` | 是否為臺北市民 |
| `nativePeople` | 是否為原住民 |

**Mock 檔案用途**

| 檔案 | 用途 |
| --- | --- |
| `account.json` | 帳號資料，微服務呼叫 userinfo 時回傳的內容 |
| `activity.json` | 首頁活動 |
| `home_banner.json` | 首頁橫幅 |
| `message.json` | 訊息頁 |
| `subscription.json` | 訂閱範例 |

> **建議**：若要展示「非市民」或「長者」情境，修改 `citizen`、`birthday` 即可切換身分。

---

## 3. WebView 開發注意事項

| 項目 | 說明 |
| --- | --- |
| ⚠️ 釋放記憶體 | 切換頁面或 App 進入背景時，請釋放 WebView 資源，以維持運作順暢。 |
| ⚠️ 雙平台測試 | 彈出視窗在 iOS 預設會被阻擋，Android 需自行處理，建議兩個平台都完整測試。 |
| 💡 於 App 內實測 | 開發時可用裝置模擬檢視，完成後請於 App 內實測；雙向溝通也需在 App 內運作。 |

---

## 4. App 與微服務溝通

微服務網頁在 WebView 中執行，可透過 `flutterObject` 請 App 執行定位、掃碼、發送通知，並將結果傳回網頁。

> **觀念**：微服務本身是一般網頁（Web），部署在外部網址（例如 `https://你的專案.web.app/`）；城市通是 Flutter App，使用者點進服務時，App 依 `destinationUrl` 用 WebView 載入這個網址。兩者之間的溝通，是「App 內的網頁（JS）↔ App 原生端（Dart）」，屬於 Hybrid 架構。
> 用一般瀏覽器（Chrome）直接開網址時沒有 `flutterObject`，因此雙向溝通只能在 App 內測試。

### 4.1 雙向溝通的運作流程

```text
微服務網頁（WebView）                         城市通 App（Flutter）
① postMessage()        ───────────────▶   ② TPWebMessageListener
   把 { name, data } 轉為 JSON 字串送出          解析 JSON，依 name 找到對應的 Handler
                                                      │
                                                      ▼
                                              ③ TPWebMessageHandler
                                                 執行定位、掃碼、發通知
                                                      │
⑤ onmessage            ◀───────────────   ④ replyWebMessage()
   從 event.data 取得 JSON 字串並解析            將結果包裝為 { name, data } 字串回傳
```

- 物件名：`flutterObject`
- 格式：`{ name, data }`，以字串傳送（物件請先 `JSON.stringify`）
- 原始碼：`lib/util/web_message_handler/`
- 底層是 flutter_inappwebview 的 WebMessageListener

### 4.2 網頁端的實作方式

```js
// 送出：postMessage 傳的是字串
window.flutterObject.postMessage(
  JSON.stringify({ name: 'location', data: null })
);

// 接收：App 回的也是 JSON 字串
const onReply = (event) => {
  const { name, data } = JSON.parse(event.data);
  if (name === 'location') {
    console.log(data.latitude, data.longitude);
  }
};
window.flutterObject.addEventListener('message', onReply);

// 用完記得移除，避免重複觸發
window.flutterObject.removeEventListener('message', onReply);
```

> **提醒**：一般瀏覽器中沒有 `flutterObject`，建議先判斷是否存在，必要時改用模擬資料。

**官方範例**：官方 Vue 微服務已封裝為 composables

- `src/composables/useConnectionMessage.ts`
- `src/composables/useHandleConnectionData.ts`

> 來源：Town Pass 開發文件「Two-Way Connection on Website」

### 4.3 以自訂 Handler 擴充 App 能力

```dart
class GreetingMessageHandler extends TPWebMessageHandler {
  @override
  String get name => 'greeting';

  @override
  Future<void> handle({
    required Object? message,
    required WebUri? sourceOrigin,
    required bool isMainFrame,
    required Function(WebMessage reply)? onReply,
  }) async {
    onReply?.call(replyWebMessage(data: '哈囉，$message！'));
  }
}
```

1. **繼承 `TPWebMessageHandler`**：寫在 `tp_web_message_handler.dart` 或新增檔案
2. **`name` 對應網頁送出的 `name`**：請避免與內建的 `location`、`notify` 等名稱重複
3. **加入清單**：加入 `TPWebMessageListener` 的 `_cachedMessageHandlers`
4. **網頁端呼叫**：`postMessage` 傳 `name: 'greeting'`、`data: '市民'`

> 去年叫 `CPWebMessageHandler`，今年改名 `TPWebMessageHandler`；路徑 `lib/util/web_message_handler/`

### 4.4 內建能力與自行擴充

| 內建（以 postMessage 直接呼叫） | 自己加（以自訂 Handler 擴充） |
| --- | --- |
| 定位 | NFC |
| QR Code 掃描 | 藍牙 |
| 手機通知 | 陀螺儀 |
| 裝置資訊 | 健康資料 |
| 撥電話、1999 | 音訊 |
| 開地圖、開連結 | 各種 IoT、Wi-Fi、AR／VR、裝置端 AI |

- 內建：網頁端傳送對應的 `name` 即可，原生功能由 App 處理
- 自己加：延續去年的項目，今年新增裝置端 AI（第 06 章）

**擴充流程**

1. **選擇開源的 Flutter 套件**：於 pub.dev 搜尋，授權為 MIT／BSD／Apache
2. **封裝為 MessageHandler**：參考 4.3 範例，自訂 `name` 並加入清單
3. **設定雙平台權限**：`Info.plist` 填寫用途說明，`AndroidManifest` 加入權限

> 套件請選開源、免費的，符合今年的規則。

---

## 5. 開發自己的服務

本節說明「服務」頁的結構、服務設定的檔案與圖示、Figma 上的設計規範與無障礙設計，最後附上賽前練習。

### 5.1 「服務」頁的四個區塊

| # | 區塊 | 說明 |
| --- | --- | --- |
| 1 | 我的服務 | 使用者自行置頂的常用服務 |
| 2 | 更多／新增 | 進入服務列表選擇置頂服務，請先將你的服務加入列表 |
| 3 | 服務拼貼 | 中央區塊，呈現重要的市政服務 |
| 4 | 熱門 | 使用頻率較高的服務 |

- 微服務通常放在「服務列表」與「熱門」
- 頁面原始碼：`lib/page/city_service/`；編輯置頂：`lib/page/city_service_edit/`

### 5.2 服務清單的設定：`my_service_model.dart`

新增服務需修改兩處：在 enum 新增 id，並於 switch 新增 case 回傳 `MyServiceItem`。

```dart
enum MyServiceItemId {
  // …現有的 21 個服務
  zoo,
  myService, // ① 新增 id
  ;
}

// ② 在 MyServiceIdExt 的 switch 補一個 case
MyServiceItemId.myService => MyServiceItem(
  title: '我的新服務',
  description: '一句話介紹這個服務',
  icon: Assets.svg.iconMyService.svg(),
  category: MyServiceCategory.cityLife,
  destinationUrl: 'https://my-service.web.app/',
),
```

**MyServiceItem 的欄位**

| 欄位 | 說明 |
| --- | --- |
| `title` | 服務名稱 |
| `description` | 一句話說明 |
| `icon` | SVG 圖示 |
| `category` | 服務列表中的分類 |
| `destinationUrl` | 點選後開啟的微服務網址（可先填測試網址，部署後再換正式網址） |
| `forceWebViewTitle` | 選填，WebView 的標題 |

**五個分類**：市政服務・防疫醫療・城市生活・探索臺北・其他服務

> 檔案：`lib/page/city_service/model/my_service_model.dart`

### 5.3 將服務加入城市通

1. **新增圖示**：將 SVG 放入 `assets/svg/`，檔名使用 snake_case，並執行 build_runner
2. **新增 id**：在 `MyServiceItemId` enum 新增一行
3. **填寫內容**：於 `MyServiceIdExt` 新增 case，`destinationUrl` 填入服務網址
4. **執行並加入**：執行 `flutter run`，於「服務 › 更多」加入我的服務

完成後，「我的服務」會出現新服務。

### 5.4 設定「熱門」與「服務拼貼」

**熱門**：`model/trending_service_model.dart`，在清單末端新增一個 `TrendingService`

```dart
static List<TrendingService> get serviceList {
  return [
    // …找地點、市政資訊儀表板、施工資訊
    TrendingService(
      title: '我的新服務',
      icon: Assets.svg.iconMyService.svg(),
      url: 'https://my-service.web.app/',
    ),
  ];
}
```

**服務拼貼**：`widget/official_service_card/`

| 位置 | 內容 |
| --- | --- |
| top_left | 市政服務 |
| top_right | 有話要說・警政報警 |
| bottom_left | 防疫醫療・市政 APP |
| bottom_right | 城市生活 |

- 四張卡片各為一個 Widget，`onTap` 目前仍為 TODO，填入網址即可導向你的服務
- 去年採 JSON 設定六個區塊，今年改為四個 Widget

> 路徑都在 `lib/page/city_service/`

### 5.5 圖示的新增與使用

```text
1 放入檔案                2 自動產生                    3 取用
assets/svg/icon_zoo.svg → (build_runner) → lib/gen/assets.gen.dart → Assets.svg.iconZoo.svg()
```

- 使用 SVG
- 檔名 snake_case（產生後會轉成 camelCase 屬性）
- 放在 `assets/svg/`
- 新增後重新 build

> 再一例：`icon_dashboard_reports.svg` → `Assets.svg.iconDashboardReports.svg()`；專案中已有 108 個圖示可直接使用。

### 5.6 Town Pass 設計資源（Figma）

**Town Pass UI Kit**：45+ 畫面、100+ 元件，免費提供色彩、字級與元件。

設計師可先以 UI Kit 組成畫面，工程師依此實作，風格與城市通一致。

> **建議**：介面是評審的第一印象，善用 UI Kit，能讓作品與城市通風格一致。

### 5.7 色票與字級規範

| 色票 | 500 色碼 |
| --- | --- |
| Primary 主色 | `#5AB4C5` |
| Secondary 輔色 | `#F5BA4B` |
| Grayscale 灰階 | `#738995` |

- 各色 50 → 950 共 11 階，500 為基準色（`TPColors.primary500` 等），另有 red、orange 狀態色
- 微服務網頁也使用同一組色票：官方 Vue 範例設定於 `tailwind.config.js`，其他框架可設為 CSS 變數

**字體**：中文 PingFang TC，英數 Roboto

**字級（TPTextStyles，單位為 Flutter 邏輯像素）**

| 樣式 | h1 | h2 | title | h3 | body | caption |
| --- | --- | --- | --- | --- | --- | --- |
| 大小 | 36 | 24 | 18 | 16 | 14 | 12 |

> 來源：`lib/util/tp_colors.dart`、`tp_text_styles.dart`

### 5.8 城市通的無障礙設計：12 類規範

| 代碼 | 類別 | 城市通的做法 |
| --- | --- | --- |
| AT | 替代文字 | 圖示可朗讀，裝飾圖已隱藏 |
| AV | 時序媒體 | 目前無影音與自動播放 |
| NT | 通知 | 系統通知與 Dialog 皆可被朗讀 |
| TS | 觸控 | 觸控目標至少 48dp × 48dp |
| FC | 焦點 | 焦點順序依上至下、左至右 |
| FM | 表單 | 欄位標籤清楚，鍵盤對應格式 |
| LK | 連結 | 描述明確，重複連結合併 |
| DC | 動態內容 | 不使用閃爍內容 |
| ST | 結構 | 每頁一個 AppBar 標題 |
| AD | 可調適 | 內容順序合乎邏輯 |
| DT | 可辨識 | 文字放大 200% 仍可閱讀 |
| PD | 可預期 | 導覽順序與圖示保持一致 |

> **期待**：城市通持續推動無障礙設計，也期待各隊在規劃微服務時，一併考量長者、視障者等不同使用者的需求。
> 來源：Town Pass 開發文件「無障礙設計」；規範代碼對照數位發展部無障礙規範
