import { onBeforeUnmount, ref } from 'vue'

/** 每 intervalMs 更新一次的目前時間 */
export function useNow(intervalMs = 30_000) {
  const now = ref(new Date())
  const timer = window.setInterval(() => {
    now.value = new Date()
  }, intervalMs)
  onBeforeUnmount(() => window.clearInterval(timer))
  return now
}
