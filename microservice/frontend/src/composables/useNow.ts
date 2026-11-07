import { onBeforeUnmount, ref } from 'vue'

/** 即時時間：預設每秒更新（首頁時間、時段狀態、預約可選時段都跟著現在時間變） */
export function useNow(intervalMs = 1_000) {
  const now = ref(new Date())
  const timer = window.setInterval(() => {
    now.value = new Date()
  }, intervalMs)
  onBeforeUnmount(() => window.clearInterval(timer))
  return now
}
