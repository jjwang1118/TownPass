import { onBeforeUnmount, onMounted, ref } from 'vue'
import type { Lang } from '@/types'

/**
 * 文字轉語音。目前使用瀏覽器 Web Speech API：
 * - 國語：zh-TW
 * - 台語：優先找 nan-TW 語音；裝置沒有台語語音時退回 zh-TW
 * 正式版若改由 App 端擴充 TTS（自訂 TPWebMessageHandler），只需替換 speak() 實作。
 */
function pickVoice(lang: Lang): SpeechSynthesisVoice | undefined {
  const voices = window.speechSynthesis?.getVoices() ?? []
  if (lang === 'nan') {
    const nan = voices.find((v) => v.lang.toLowerCase().startsWith('nan'))
    if (nan) return nan
  }
  return (
    voices.find((v) => v.lang === 'zh-TW') ??
    voices.find((v) => v.lang.toLowerCase().startsWith('zh-hant')) ??
    voices.find((v) => v.lang.toLowerCase().startsWith('zh'))
  )
}

export function speak(text: string, lang: Lang = 'zh'): void {
  const synth = window.speechSynthesis
  if (!synth || !text) return
  synth.cancel()
  const utter = new SpeechSynthesisUtterance(text)
  const voice = pickVoice(lang)
  if (voice) utter.voice = voice
  utter.lang = voice?.lang ?? 'zh-TW'
  utter.rate = 0.85 // 長者使用，語速放慢
  synth.speak(utter)
}

export function stopSpeaking(): void {
  window.speechSynthesis?.cancel()
}

/** 頁面用：離開頁面或 App 進入背景時停止朗讀 */
export function useTts() {
  const speaking = ref(false)
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
