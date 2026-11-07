<script setup lang="ts">
/** EL-STP-01 數量選擇器：每次增減半顆，最小值半顆 */
import { amountText } from '@/utils/schedule'

const model = defineModel<number>({ required: true })
defineProps<{ label: string }>()

const MIN = 0.5
const MAX = 10

function dec() {
  model.value = Math.max(MIN, model.value - 0.5)
}
function inc() {
  model.value = Math.min(MAX, model.value + 0.5)
}
</script>

<template>
  <div class="el-stp-01" role="group" :aria-label="label">
    <button type="button" class="step font-h2-semibold" aria-label="減少半顆" :disabled="model <= MIN" @click="dec">
      －
    </button>
    <span class="value font-h2-semibold" aria-live="polite">{{ amountText(model) }}</span>
    <button type="button" class="step font-h2-semibold" aria-label="增加半顆" :disabled="model >= MAX" @click="inc">
      ＋
    </button>
  </div>
</template>

<style scoped>
.el-stp-01 {
  width: 100%;
  min-height: 64px;
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 8px;
  border-radius: 12px;
  background: var(--color-grey-50);
}
.step {
  width: 48px;
  height: 48px;
  border-radius: 8px;
  border: 1px solid var(--color-primary-700);
  background: var(--background-color);
  color: var(--color-primary-700);
}
.step:disabled {
  opacity: 0.4;
}
.value {
  color: var(--text-primary);
}
</style>
