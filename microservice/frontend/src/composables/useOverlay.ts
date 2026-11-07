import { nextTick, onBeforeUnmount, watch, type Ref } from 'vue'

/**
 * 彈窗／底部抽屜共用：開啟時聚焦第一個可聚焦元素、Esc 關閉、焦點鎖在內部、關閉後焦點回到觸發元素。
 */
export function useOverlay(open: Ref<boolean>, panel: Ref<HTMLElement | null>, close: () => void) {
  let returnFocus: HTMLElement | null = null

  const focusables = () =>
    Array.from(
      panel.value?.querySelectorAll<HTMLElement>('button:not([disabled]), [href], input, [tabindex]:not([tabindex="-1"])') ?? [],
    )

  const onKey = (e: KeyboardEvent) => {
    if (e.key === 'Escape') {
      e.preventDefault()
      close()
      return
    }
    if (e.key !== 'Tab') return
    const list = focusables()
    if (list.length === 0) return
    const first = list[0]
    const last = list[list.length - 1]
    if (e.shiftKey && document.activeElement === first) {
      e.preventDefault()
      last.focus()
    } else if (!e.shiftKey && document.activeElement === last) {
      e.preventDefault()
      first.focus()
    }
  }

  watch(open, async (v) => {
    if (v) {
      returnFocus = document.activeElement as HTMLElement | null
      document.addEventListener('keydown', onKey)
      document.body.style.overflow = 'hidden'
      await nextTick()
      ;(panel.value?.querySelector<HTMLElement>('[data-autofocus]') ?? focusables()[0] ?? panel.value)?.focus()
    } else {
      document.removeEventListener('keydown', onKey)
      document.body.style.overflow = ''
      returnFocus?.focus?.()
      returnFocus = null
    }
  })

  onBeforeUnmount(() => {
    document.removeEventListener('keydown', onKey)
    document.body.style.overflow = ''
  })
}
