import { onBeforeUnmount, ref } from 'vue'

/** 即時時間：預設每秒更新（首頁時間、時段狀態、預約可選時段都跟著現在時間變） */
export function useNow(intervalMs = 1_000) {
  const now = ref(new Date())
  const update = () => {
    now.value = new Date()
  }
  const onVisibilityChange = () => {
    if (document.visibilityState === 'visible') update()
  }
  const timer = window.setInterval(update, intervalMs)
  document.addEventListener('visibilitychange', onVisibilityChange)
  window.addEventListener('focus', update)
  onBeforeUnmount(() => {
    window.clearInterval(timer)
    document.removeEventListener('visibilitychange', onVisibilityChange)
    window.removeEventListener('focus', update)
  })
  return now
}
