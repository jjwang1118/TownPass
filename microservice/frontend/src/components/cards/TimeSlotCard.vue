<script setup lang="ts">
/** CM-CRD-02 時段格（已過／現在／等一下） */
import { computed } from 'vue'
import type { SlotStatus } from '@/types'

const props = defineProps<{ name: string; time: string; codes: string[]; status: SlotStatus }>()
const emit = defineEmits<{ click: [] }>()

const statusText = computed(() => ({ past: '已過', now: '現在', later: '等一下' })[props.status])
const codesText = computed(() => (props.codes.length ? props.codes.join('　') : '不用吃藥'))
</script>

<template>
  <button
    type="button"
    class="cm-crd-02"
    :class="status"
    :aria-label="`${name} ${time}，${statusText}，${codes.length ? codes.join('、') : '不用吃藥'}`"
    @click="emit('click')"
  >
    <span class="head">
      <span class="name font-h3-semibold">{{ name }}</span>
      <span class="tag font-h3-semibold">{{ statusText }}</span>
    </span>
    <span class="time font-h2-semibold">{{ time }}</span>
    <span class="codes font-h3-regular">{{ codesText }}</span>
  </button>
</template>

<style scoped>
.cm-crd-02 {
  width: 100%;
  min-height: 48px;
  display: flex;
  flex-direction: column;
  gap: 6px;
  padding: 12px;
  border-radius: 12px;
  text-align: left;
  border: 1px solid var(--color-grey-200);
  background: var(--background-color);
}
.head {
  display: flex;
  justify-content: space-between;
  align-items: center;
  gap: 4px;
  flex-wrap: wrap;
}
.tag {
  padding: 0 8px;
  border-radius: 12px;
  background: var(--color-grey-100);
  color: var(--text-second);
}
.name,
.time {
  color: var(--text-primary);
}
.codes {
  color: var(--text-second);
}
.past {
  background: var(--color-grey-50);
}
.past .name,
.past .time {
  color: var(--text-second);
}
.now {
  background: var(--color-primary-50);
  border: 2px solid var(--color-primary-500);
  padding: 11px;
}
.now .tag {
  background: var(--color-primary-500);
  color: var(--color-white);
}
</style>
