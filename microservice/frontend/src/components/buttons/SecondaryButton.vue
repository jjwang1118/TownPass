<script setup lang="ts">
/** CM-BTN-03 次要按鈕（外框，TownPass 48/Button Second）；size：standard（獨佔一行）／narrow（flex-1、高 48） */
withDefaults(defineProps<{ size?: 'standard' | 'narrow' }>(), { size: 'standard' })
const emit = defineEmits<{ click: [] }>()
</script>

<template>
  <button type="button" class="cm-btn-03 font-h3-regular" :class="size" @click="emit('click')">
    <slot />
  </button>
</template>

<style scoped>
.cm-btn-03 {
  display: flex;
  align-items: center;
  justify-content: center;
  text-align: center;
  padding: 8px 16px;
  border-radius: 10px;
  border: 1px solid var(--color-primary-500);
  background: var(--background-color);
  color: var(--color-primary-500);
}
.standard {
  width: 100%;
  min-height: 56px;
}
.narrow {
  flex: 1 1 0;
  min-height: 48px;
}
</style>
