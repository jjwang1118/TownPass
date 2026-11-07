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
- **語音**：依 `lang` 挑語音，離線語音優先，找不到該語言就失敗，不會用別的語言硬念。
  - 中文（`zh-TW`，預設）：台灣中文優先，不使用粵語（zh-HK）
  - 英文（`en-US`）：美式英文優先，其次其他英文（en-GB…），給外籍看護聽 `speech_text_en`
- **語速** 預設 0.85（比一般慢），可用 `speak(text, { rate })` 調整。
- **長句**依句尾標點分段念，避免部分瀏覽器念到一半中斷。
- **切換頁面或 App 進入背景時自動停止**，釋放資源。
- **一般瀏覽器**（沒有 `flutterObject`）會略過 ①，直接用 ②。

| 平台 | ① App handler | ② speechSynthesis |
|---|---|---|
| iOS（WKWebView） | ✅ 已實作 | 一般可用；第一次要由使用者點擊觸發，靜音模式可能沒聲音 |
| Android（WebView） | ✅ 已實作 | ❌ 實測不支援（Android WebView 沒有 speechSynthesis），**只能靠 ①** |

## 在前端使用

```ts
import { speak, stop } from '@/tts/tts.js'; // 路徑依前端專案調整

async function onReadAloud(speechText: string) {
  const result = await speak(speechText); // speechText 來自後端 API 的 speech_text
  if (!result.ok) {
    // 無法朗讀：提示「這支手機不支援朗讀」，畫面維持大字顯示
  }
}

// 「Read in English」按鈕：念後端的 speech_text_en
await speak(speechTextEn, { lang: 'en-US' });

// 離開頁面時（例如 Vue 的 onUnmounted）
stop();
```

- **要由按鈕觸發**：WebView 通常不允許頁面一打開就自動出聲。提醒畫面請放一個大的「念給我聽」按鈕。
- 回傳值：`{ ok, engine: 'app' | 'web', reason }`。App 引擎在**開始朗讀時**回傳，網頁引擎在**念完時**回傳。

## App handler 約定（①）

已實作於 `lib/util/web_message_handler/tts_message_handler.dart`（`flutter_tts`，MIT 授權），註冊在 `tp_web_message_listener.dart`。

- **只用離線語音**：Android 會略過需要網路的語音（`network_required`），找不到就回覆 `no_offline_voice`，不會改走雲端。
- Android 手機裡有 Google 語音引擎時優先使用；iOS 設定為靜音模式也能播放。
- WebView 建立時就先初始化引擎；App 每一步都有時間限制，保證回覆，過程以 `[tts]` 開頭印在 logcat。
- 模組等 12 秒沒收到回覆就送出 `tts_stop` 並改用 ②；下次朗讀仍會再試 App（第一次失敗不會記住）。

| name | 網頁送出的 data | App 回覆 |
|---|---|---|
| `tts_speak` | `{ text: string, lang: 'zh-TW', rate: 0.85 }`（rate 以 1.0 為正常語速） | **開始朗讀或失敗時**回覆一次：`{ ok: true }` 或 `{ ok: false, reason }`；reason 例如 `no_offline_voice`、`no_chinese_voice`、`engine_init_timeout`、`voice_list_timeout`、`speak_timeout`、`empty_text`、`app_error` |
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
