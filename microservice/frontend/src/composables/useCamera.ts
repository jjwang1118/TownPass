import { onBeforeUnmount, onMounted, ref, type Ref } from 'vue'

/**
 * 相機預覽（EL-CRD-06／EL-CRD-07）。
 * 切換頁面或 App 進入背景時釋放相機資源，回到前景時重新開啟。
 */
export function useCamera(video: Ref<HTMLVideoElement | null>) {
  const error = ref('')
  const ready = ref(false)
  let stream: MediaStream | null = null

  async function start() {
    if (stream) return
    if (!navigator.mediaDevices?.getUserMedia) {
      error.value = '無法開啟相機'
      return
    }
    try {
      stream = await navigator.mediaDevices.getUserMedia({
        video: { facingMode: 'environment' },
        audio: false,
      })
      if (video.value) {
        video.value.srcObject = stream
        await video.value.play().catch(() => undefined)
      }
      error.value = ''
      ready.value = true
    } catch {
      error.value = '無法開啟相機，請確認已允許使用相機'
      ready.value = false
    }
  }

  function stop() {
    stream?.getTracks().forEach((t) => t.stop())
    stream = null
    ready.value = false
    if (video.value) video.value.srcObject = null
  }

  const onVisibility = () => {
    if (document.visibilityState === 'hidden') stop()
    else void start()
  }

  onMounted(() => {
    void start()
    document.addEventListener('visibilitychange', onVisibility)
  })
  onBeforeUnmount(() => {
    document.removeEventListener('visibilitychange', onVisibility)
    stop()
  })

  return { error, ready, start, stop }
}
