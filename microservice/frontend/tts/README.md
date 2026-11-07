# tts — 朗讀模組

給微服務網頁用的朗讀功能，不依賴框架或套件，Android、iOS 的 WebView 都能用。前端只要呼叫 `speak(text)`。

| 檔案 | 內容 |
|---|---|
| `tts.js` | 模組本體（ES module） |
| `tts.d.ts` | TypeScript 型別宣告 |
| `index.html` | 測試頁：朗讀、停止、環境檢查 |

## 運作方式

```
speak(text)
  ├─ ① App 的 tts_speak handler（手機內建 TTS）  在城市通 App 裡、且 App 有這個 handler 時
  ├─ ② 網頁 speechSynthesis                       瀏覽器有中文語音時
  └─ ③ 都不行 → 回傳 { ok: false }                畫面改為只顯示大字
```

- **全部在手機上合成**，不呼叫雲端服務，符合比賽「推論在裝置端」的規定；不需要下載模型。
- **語音**：台灣中文優先、離線語音優先；找不到中文語音就失敗，不會用英文語音硬念。
- **語速** 預設 0.85（比一般慢），可用 `speak(text, { rate })` 調整。
- **長句**依句尾標點分段念，避免部分瀏覽器念到一半中斷。
- **切換頁面或 App 進入背景時自動停止**，釋放資源。
- **一般瀏覽器**（沒有 `flutterObject`）會略過 ①，直接用 ②。

| 平台 | ① App handler | ② speechSynthesis |
|---|---|---|
| iOS（WKWebView） | App 加上 handler 後可用 | 一般可用；第一次要由使用者點擊觸發，靜音模式可能沒聲音 |
| Android（WebView） | App 加上 handler 後可用 | **不一定能用**，要用測試頁實測 |

## 在前端使用

```ts
import { speak, stop } from '@/tts/tts.js'; // 路徑依前端專案調整

async function onReadAloud(speechText: string) {
  const result = await speak(speechText); // speechText 來自後端 API 的 speech_text
  if (!result.ok) {
    // 無法朗讀：提示「這支手機不支援朗讀」，畫面維持大字顯示
  }
}

// 離開頁面時（例如 Vue 的 onUnmounted）
stop();
```

- **要由按鈕觸發**：WebView 通常不允許頁面一打開就自動出聲。提醒畫面請放一個大的「念給我聽」按鈕。
- 回傳值：`{ ok, engine: 'app' | 'web', reason }`。App 引擎在**開始朗讀時**回傳，網頁引擎在**念完時**回傳。

## App handler 約定（① 需要 App 配合）

App 加上以下 handler 後，模組會自動改用手機內建 TTS（建議用 `flutter_tts`，MIT 授權）。沒有加的話，模組等 2 秒沒收到回覆就改用 ②，之後同一頁不會再等。

| name | 網頁送出的 data | App 回覆 |
|---|---|---|
| `tts_speak` | `{ text: string, lang: 'zh-TW', rate: 0.85 }` | **開始朗讀或失敗時**回覆一次：`{ ok: true }` 或 `{ ok: false, reason: string }` |
| `tts_stop` | `null` | 不用回覆 |

## 測試

**電腦瀏覽器**：在 `microservice/frontend` 執行 `python -m http.server 5173`，開啟 <http://localhost:5173/tts/>。

**城市通 App（Android Studio 模擬器）**：WebView 的結果才算數，電腦瀏覽器或模擬器裡的 Chrome 能念，不代表 WebView 能念。

1. 模擬器使用有 **Google Play** 標示的系統映像，並在「設定 › 系統 › 語言 › 文字轉語音輸出」確認中文（台灣）語音可以試聽。
2. 在電腦的 `microservice/frontend` 執行 `python -m http.server 5173`。
3. 暫時把 `lib/page/city_service/model/my_service_model.dart` 中「呷藥囉」（`elderlyCare`）的 `destinationUrl` 改成 `http://10.0.2.2:5173/tts/`，執行 App（debug 版已允許以 http 連 `10.0.2.2`）。**不要 commit 這個改動。**
4. 開啟「呷藥囉」，看「環境檢查」：
   - 「使用的語音」有中文 → 按「念給我聽」，聽得到就代表 ② 在 Android WebView 可用
   - 「沒有中文語音」或狀態顯示「已呼叫但沒有開始念」→ Android 需要 ① App handler
5. 開飛航模式再按一次，確認離線也能念。

自動測試（Node 模擬瀏覽器）涵蓋：分段、挑語音、沒有中文語音、WebView 靜默失敗、App 有／沒有 handler 的切換。
