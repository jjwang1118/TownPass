<script setup lang="ts">
/** CM-BTN-02 主要按鈕（啟用／停用） */
withDefaults(defineProps<{ disabled?: boolean; type?: 'button' | 'submit' }>(), {
  disabled: false,
  type: 'button',
})
const emit = defineEmits<{ click: [] }>()
</script>

<template>
  <button :type="type" class="cm-btn-02 font-h3-regular" :disabled="disabled" @click="emit('click')">
    <slot />
  </button>
</template>

<style scoped>
.cm-btn-02 {
  width: 100%;
  min-height: 56px;
  padding: 8px 16px;
  border-radius: 10px;
  background: var(--color-primary-500);
  color: var(--color-white);
  display: flex;
  align-items: center;
  justify-content: center;
  text-align: center;
}
.cm-btn-02:disabled {
  background: var(--color-grey-100);
  color: var(--color-grey-500);
}
</style>
