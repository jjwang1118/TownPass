// 朗讀模組：多引擎自動切換，不依賴任何框架或套件。
//
//   speak(text)
//     ① App 的 tts_speak handler（手機內建 TTS）：在城市通 App 裡、且 App 已加上 handler 時使用
//     ② 網頁 speechSynthesis：瀏覽器有中文語音時使用（iOS WebView 通常可以，Android WebView 要實測）
//     ③ 都不行：回傳 { ok: false }，畫面應改為只顯示大字
//
// 全部在手機上合成，不呼叫任何雲端服務（比賽規定：推論在裝置端）。

const DEFAULT_LANG = 'zh-TW';
const DEFAULT_RATE = 0.85; // 長輩聽：比預設慢一點
const APP_REPLY_TIMEOUT_MS = 12000; // App 每一步都有時間限制，最慢約 10 秒內一定回覆；超過代表 App 沒有 tts_speak handler
const VOICES_TIMEOUT_MS = 1500; // 語音清單是非同步載入的
const START_TIMEOUT_MS = 3000; // 呼叫後一直沒開始念（Android WebView 可能靜默失敗）
const MAX_CHUNK = 80; // 部分瀏覽器念太長的句子會中斷，所以分段

// null：還沒試過；true：App 有回覆過；false：最近一次沒回覆。
// 只用於診斷顯示，不會因為 false 就跳過 App（第一次可能只是引擎初始化太慢）。
let appHandlerAvailable = null;
let lifecycleBound = false;

// ---------- 共用 ----------

function hasWindow() {
  return typeof window !== 'undefined';
}

function flutterObject() {
  return hasWindow() ? window.flutterObject : undefined;
}

function webSpeech() {
  return hasWindow() && 'speechSynthesis' in window && 'SpeechSynthesisUtterance' in window
    ? window.speechSynthesis
    : undefined;
}

/** 依句尾標點分段，每段不超過 MAX_CHUNK 字。 */
export function splitText(text) {
  const sentences = String(text)
    .replace(/\s+/g, ' ')
    .split(/(?<=[。！？!?；;～~\n])/)
    .map((s) => s.trim())
    .filter(Boolean);
  const chunks = [];
  for (const sentence of sentences) {
    if (sentence.length <= MAX_CHUNK) {
      chunks.push(sentence);
      continue;
    }
    // 句子太長：再用逗號、頓號切，仍太長就硬切
    let current = '';
    for (const part of sentence.split(/(?<=[，,、])/)) {
      if ((current + part).length > MAX_CHUNK && current) {
        chunks.push(current);
        current = '';
      }
      current += part;
      while (current.length > MAX_CHUNK) {
        chunks.push(current.slice(0, MAX_CHUNK));
        current = current.slice(MAX_CHUNK);
      }
    }
    if (current) chunks.push(current);
  }
  return chunks;
}

// ---------- ① App handler ----------

/**
 * 請 App 用手機內建 TTS 朗讀。
 * 約定：App 開始朗讀（或失敗）時回覆一次 { name: 'tts_speak', data: { ok, reason? } }。
 * App 沒有這個 handler 時不會回覆，等 APP_REPLY_TIMEOUT_MS 後改用下一個引擎；下次朗讀仍會再試 App。
 */
function speakWithApp(text, { lang, rate }) {
  const bridge = flutterObject();
  if (!bridge) {
    return Promise.resolve({ ok: false, reason: 'not_in_app' });
  }
  return new Promise((resolve) => {
    const onMessage = (event) => {
      let message;
      try {
        message = JSON.parse(event.data);
      } catch {
        return;
      }
      if (message?.name !== 'tts_speak') return;
      cleanup();
      appHandlerAvailable = true;
      const data = message.data ?? {};
      resolve(data.ok ? { ok: true } : { ok: false, reason: data.reason || 'app_failed' });
    };
    const timer = setTimeout(() => {
      cleanup();
      appHandlerAvailable = false;
      // App 若只是太慢，避免它在我們改用其他引擎後才開始念
      bridge.postMessage(JSON.stringify({ name: 'tts_stop', data: null }));
      resolve({ ok: false, reason: 'app_no_reply' });
    }, APP_REPLY_TIMEOUT_MS);
    function cleanup() {
      clearTimeout(timer);
      bridge.removeEventListener('message', onMessage); // 用完移除，避免重複觸發
    }
    bridge.addEventListener('message', onMessage);
    bridge.postMessage(JSON.stringify({ name: 'tts_speak', data: { text, lang, rate } }));
  });
}

function stopApp() {
  const bridge = flutterObject();
  if (bridge && appHandlerAvailable !== null) {
    bridge.postMessage(JSON.stringify({ name: 'tts_stop', data: null }));
  }
}

// ---------- ② 網頁 speechSynthesis ----------

function loadVoices() {
  const synth = webSpeech();
  if (!synth) return Promise.resolve([]);
  const now = synth.getVoices();
  if (now.length) return Promise.resolve(now);
  return new Promise((resolve) => {
    const done = () => {
      clearTimeout(timer);
      synth.removeEventListener?.('voiceschanged', done);
      resolve(synth.getVoices());
    };
    const timer = setTimeout(done, VOICES_TIMEOUT_MS);
    synth.addEventListener?.('voiceschanged', done);
  });
}

function normLang(lang) {
  return String(lang || '').replace('_', '-').toLowerCase();
}

/**
 * 挑語音：語言完全相同優先、離線語音優先；找不到該語言就回傳 null（不用別的語言硬念）。
 * - 中文（zh-*）：台灣中文優先；粵語（zh-HK、yue）不使用，念出來長輩聽不懂
 * - 其他語言（例如 en-US）：相同語言優先，其次同語系（en-GB、en-AU…）
 */
export function pickVoice(voices, lang = DEFAULT_LANG) {
  const target = normLang(lang);
  const base = target.split('-')[0];
  const chinese = base === 'zh' || base === 'cmn';
  const score = (v) => {
    const l = normLang(v.lang);
    let s = 0;
    if (l === target) s = 100;
    else if (chinese) {
      if (l === 'cmn-hant-tw' || l === 'zh-hant-tw') s = 90;
      else if (l.startsWith('zh-hk') || l.startsWith('yue')) return -1;
      else if (l.startsWith('zh') || l.startsWith('cmn')) s = 40;
      else return -1;
    } else if (l.split('-')[0] === base) s = 50;
    else return -1;
    if (v.localService) s += 5; // 離線語音
    return s;
  };
  const ranked = voices.map((v) => [score(v), v]).filter(([s]) => s >= 0);
  ranked.sort((a, b) => b[0] - a[0]);
  return ranked.length ? ranked[0][1] : null;
}

function speakChunk(synth, chunk, voice, rate) {
  return new Promise((resolve) => {
    const utterance = new window.SpeechSynthesisUtterance(chunk);
    utterance.voice = voice;
    utterance.lang = voice.lang;
    utterance.rate = rate;
    let started = false;
    const timer = setTimeout(() => {
      if (!started) {
        synth.cancel();
        resolve({ ok: false, reason: 'web_speech_no_start' });
      }
    }, START_TIMEOUT_MS);
    utterance.onstart = () => {
      started = true;
      clearTimeout(timer);
    };
    utterance.onend = () => {
      clearTimeout(timer);
      resolve({ ok: true, started });
    };
    utterance.onerror = (e) => {
      clearTimeout(timer);
      // cancel() 造成的中斷不算失敗
      const interrupted = e.error === 'interrupted' || e.error === 'canceled';
      resolve(interrupted ? { ok: true, started, interrupted: true } : { ok: false, reason: `web_speech_${e.error || 'error'}` });
    };
    synth.speak(utterance);
  });
}

async function speakWithWeb(text, { lang, rate }) {
  const synth = webSpeech();
  if (!synth) return { ok: false, reason: 'no_web_speech' };
  const voice = pickVoice(await loadVoices(), lang);
  if (!voice) return { ok: false, reason: normLang(lang).startsWith('zh') ? 'no_chinese_voice' : 'no_voice_for_language' };
  synth.cancel(); // 清掉上一段
  const chunks = splitText(text);
  let anyStarted = false;
  for (const chunk of chunks) {
    const result = await speakChunk(synth, chunk, voice, rate);
    if (!result.ok) return anyStarted ? { ok: true, partial: true } : result;
    anyStarted = anyStarted || result.started;
    if (result.interrupted) break;
  }
  return { ok: true };
}

// ---------- 對外 API ----------

/**
 * 朗讀文字，依序嘗試 App handler → 網頁 speechSynthesis。
 * @returns {Promise<{ok: boolean, engine?: 'app'|'web', reason?: string}>}
 *   App 引擎在開始朗讀時就回傳；網頁引擎在念完時回傳。
 *   ok 為 false 時，畫面應改為只顯示大字。
 */
export async function speak(text, { lang = DEFAULT_LANG, rate = DEFAULT_RATE } = {}) {
  bindLifecycle();
  const content = String(text ?? '').trim();
  if (!content) return { ok: false, reason: 'empty_text' };
  stop();

  const reasons = [];
  const app = await speakWithApp(content, { lang, rate });
  if (app.ok) return { ok: true, engine: 'app' };
  reasons.push(app.reason);

  const web = await speakWithWeb(content, { lang, rate });
  if (web.ok) return { ok: true, engine: 'web' };
  reasons.push(web.reason);

  return { ok: false, reason: reasons.join(',') };
}

/** 停止朗讀（兩個引擎都停）。 */
export function stop() {
  stopApp();
  webSpeech()?.cancel();
}

/** 診斷目前環境：測試頁與除錯用。 */
export async function diagnose(lang = DEFAULT_LANG) {
  const voices = await loadVoices();
  const chosen = pickVoice(voices, lang);
  return {
    inApp: Boolean(flutterObject()),
    appHandler: appHandlerAvailable, // null 表示還沒試過
    webSpeech: Boolean(webSpeech()),
    voices: voices.map((v) => ({ name: v.name, lang: v.lang, localService: v.localService })),
    chosenVoice: chosen ? { name: chosen.name, lang: chosen.lang, localService: chosen.localService } : null,
    userAgent: hasWindow() ? navigator.userAgent : '',
  };
}

/** 切換頁面或 App 進入背景時停止朗讀，釋放資源。 */
function bindLifecycle() {
  if (lifecycleBound || !hasWindow()) return;
  lifecycleBound = true;
  document.addEventListener('visibilitychange', () => {
    if (document.visibilityState === 'hidden') stop();
  });
  window.addEventListener('pagehide', stop);
}
