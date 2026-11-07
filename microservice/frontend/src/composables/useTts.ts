import { onBeforeUnmount, onMounted, ref } from 'vue'
import type { Lang } from '@/types'
import { speak as ttsSpeak, stop as ttsStop } from '../../tts/tts.js'

/**
 * 文字轉語音：使用 tts/tts.js（見 tts/README.md）。
 * - 在城市通 App 裡：App 的 tts_speak handler（手機內建離線語音；Android WebView 沒有 speechSynthesis，只能靠這個）
 * - 一般瀏覽器：網頁 speechSynthesis
 * - 國語念 zh-TW，英文念 en-US（給外籍看護）
 */
const VOICE_LANG: Record<Lang, string> = { zh: 'zh-TW', en: 'en-US' }

const speaking = ref(false)

export async function speak(text: string, lang: Lang = 'zh'): Promise<boolean> {
  if (!text) return false
  speaking.value = true
  try {
    const result = await ttsSpeak(text, { lang: VOICE_LANG[lang] ?? 'zh-TW' })
    if (!result.ok) console.warn('[tts] 無法朗讀', result.reason)
    return result.ok
  } finally {
    speaking.value = false
  }
}

export function stopSpeaking(): void {
  ttsStop()
  speaking.value = false
}

/** 頁面用：離開頁面或 App 進入背景時停止朗讀 */
export function useTts() {
  const onHidden = () => {
    if (document.visibilityState === 'hidden') stopSpeaking()
  }
  onMounted(() => document.addEventListener('visibilitychange', onHidden))
  onBeforeUnmount(() => {
    document.removeEventListener('visibilitychange', onHidden)
    stopSpeaking()
  })
  return { speak, stop: stopSpeaking, speaking }
}
