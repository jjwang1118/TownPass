<script setup lang="ts">
/** EL-MD-01 長者：取消綁定確認（彈窗） */
import { ref, toRef, useId } from 'vue'
import { useOverlay } from '@/composables/useOverlay'

const props = defineProps<{ open: boolean; familyName: string }>()
const emit = defineEmits<{ close: []; confirm: [] }>()

const panel = ref<HTMLElement | null>(null)
const titleId = useId()
const descId = useId()
useOverlay(toRef(props, 'open'), panel, () => emit('close'))
</script>

<template>
  <Teleport to="body">
    <div v-if="open" class="el-md-01">
      <div class="mask" aria-hidden="true" @click="emit('close')" />
      <div
        ref="panel"
        class="dialog"
        role="alertdialog"
        aria-modal="true"
        :aria-labelledby="titleId"
        :aria-describedby="descId"
      >
        <h2 :id="titleId" class="title font-h2-semibold">確定要取消綁定？</h2>
        <p :id="descId" class="desc font-h3-regular">
          取消後，{{ familyName }} 將不再收到您的用藥與回診提醒。
        </p>
        <div class="actions">
          <button type="button" class="btn danger font-h3-regular" @click="emit('confirm')">取消綁定</button>
          <button type="button" class="btn secondary font-h3-regular" data-autofocus @click="emit('close')">
            再想想
          </button>
        </div>
      </div>
    </div>
  </Teleport>
</template>

<style scoped>
.el-md-01 {
  position: fixed;
  inset: 0;
  z-index: 100;
  display: flex;
  align-items: center;
  justify-content: center;
  padding: 16px;
}
.mask {
  position: absolute;
  inset: 0;
  background: var(--overlay);
}
.dialog {
  position: relative;
  width: 311px;
  max-width: 100%;
  max-height: 90dvh;
  overflow-y: auto;
  display: flex;
  flex-direction: column;
  gap: 16px;
  padding: 24px;
  border-radius: 16px;
  background: var(--background-color);
}
.title {
  color: var(--text-primary);
}
.desc {
  color: var(--text-second);
}
.actions {
  display: flex;
  flex-wrap: wrap;
  gap: 12px;
}
.btn {
  flex: 1 1 0;
  min-width: 112px;
  min-height: 48px;
  padding: 8px 12px;
  border-radius: 10px;
}
.danger {
  background: var(--alarm-red-500);
  color: var(--color-white);
}
.secondary {
  background: var(--background-color);
  color: var(--color-primary-500);
  border: 1px solid var(--color-primary-500);
}
</style>
