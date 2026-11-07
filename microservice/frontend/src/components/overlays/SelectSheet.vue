<script setup lang="ts">
/**
 * CM-SH-01 選擇清單（底部抽屜）
 * - 點遮罩關閉、不異動原選擇
 * - 額滿／不可選的選項灰階且不可點
 * - showCheck：目前選中項顯示打勾＋主色外框／底色（RE-PG-01）
 */
import { ref, toRef, useId } from 'vue'
import AppIcon from '@/components/AppIcon.vue'
import { useOverlay } from '@/composables/useOverlay'
import type { SelectOption } from '@/types'

const props = withDefaults(
  defineProps<{
    open: boolean
    title: string
    options: SelectOption[]
    selected?: string
    showCheck?: boolean
  }>(),
  { selected: '', showCheck: false },
)
const emit = defineEmits<{ close: []; select: [value: string] }>()

const panel = ref<HTMLElement | null>(null)
const titleId = useId()
useOverlay(toRef(props, 'open'), panel, () => emit('close'))

function choose(opt: SelectOption) {
  if (opt.disabled) return
  emit('select', opt.value)
}
</script>

<template>
  <Teleport to="body">
    <Transition name="sheet">
      <div v-if="open" class="cm-sh-01">
        <div class="mask" aria-hidden="true" @click="emit('close')" />
        <div ref="panel" class="panel" role="dialog" aria-modal="true" :aria-labelledby="titleId" tabindex="-1">
          <h2 :id="titleId" class="title font-h2-semibold">{{ title }}</h2>
          <p class="hint font-h3-regular">上下滑動看更多選項</p>
          <ul class="list">
            <li v-for="opt in options" :key="opt.value">
              <button
                type="button"
                class="option"
                :class="{ disabled: opt.disabled, current: showCheck && opt.value === selected }"
                :aria-disabled="opt.disabled || undefined"
                :aria-current="opt.value === selected || undefined"
                :data-autofocus="opt.value === selected ? '' : undefined"
                @click="choose(opt)"
              >
                <span class="texts">
                  <span class="main font-h3-semibold">{{ opt.label }}</span>
                  <span v-if="opt.subtitle" class="sub font-h3-regular">{{ opt.subtitle }}</span>
                </span>
                <AppIcon v-if="showCheck && opt.value === selected" name="check" />
              </button>
            </li>
          </ul>
          <button type="button" class="sr-only" @click="emit('close')">關閉選單</button>
        </div>
      </div>
    </Transition>
  </Teleport>
</template>

<style scoped>
.cm-sh-01 {
  position: fixed;
  inset: 0;
  z-index: 100;
  display: flex;
  flex-direction: column;
  justify-content: flex-end;
}
.mask {
  position: absolute;
  inset: 0;
  background: var(--overlay);
}
.panel {
  position: relative;
  width: 100%;
  max-width: 480px;
  margin: 0 auto;
  max-height: 90dvh;
  display: flex;
  flex-direction: column;
  gap: 8px;
  padding: 20px 16px calc(32px + env(safe-area-inset-bottom));
  border-radius: 16px 16px 0 0;
  background: var(--background-color);
  outline: none;
}
.title {
  color: var(--text-primary);
}
.hint {
  color: var(--text-second);
}
.list {
  list-style: none;
  margin: 8px 0 0;
  padding: 0;
  display: flex;
  flex-direction: column;
  gap: 8px;
  height: 440px;
  max-height: 60dvh;
  overflow-y: auto;
  overscroll-behavior: contain;
}
.option {
  width: 100%;
  min-height: 56px;
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
  padding: 12px 16px;
  border-radius: 12px;
  border: 1px solid var(--color-grey-200);
  background: var(--background-color);
  text-align: left;
  color: var(--text-primary);
}
.option.current {
  border: 2px solid var(--color-primary-500);
  background: var(--color-primary-50);
  color: var(--color-primary-700);
}
.option.disabled {
  background: var(--color-grey-50);
  color: var(--text-direction);
  cursor: not-allowed;
}
.texts {
  display: flex;
  flex-direction: column;
  gap: 2px;
}
.sub {
  color: var(--text-second);
}
.option.disabled .sub {
  color: var(--text-direction);
}
.sheet-enter-active,
.sheet-leave-active {
  transition: opacity 0.2s ease;
}
.sheet-enter-active .panel,
.sheet-leave-active .panel {
  transition: transform 0.2s ease;
}
.sheet-enter-from,
.sheet-leave-to {
  opacity: 0;
}
.sheet-enter-from .panel,
.sheet-leave-to .panel {
  transform: translateY(100%);
}
</style>
