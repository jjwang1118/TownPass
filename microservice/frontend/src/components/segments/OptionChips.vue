<script setup lang="ts">
/** EL-SEG-02 選項晶片組；multiple=true 複選，否則單選 */
const props = withDefaults(
  defineProps<{ options: readonly string[]; multiple?: boolean; label: string; required?: boolean }>(),
  { multiple: false, required: false },
)
const model = defineModel<string | string[]>({ required: true })

function isSelected(opt: string): boolean {
  return Array.isArray(model.value) ? model.value.includes(opt) : model.value === opt
}

function toggle(opt: string) {
  if (props.multiple) {
    const list = Array.isArray(model.value) ? [...model.value] : []
    const idx = list.indexOf(opt)
    if (idx >= 0) list.splice(idx, 1)
    else list.push(opt)
    model.value = list
  } else {
    model.value = opt
  }
}
</script>

<template>
  <div
    class="el-seg-02"
    :role="multiple ? 'group' : 'radiogroup'"
    :aria-label="label"
    :aria-required="required || undefined"
  >
    <button
      v-for="opt in options"
      :key="opt"
      type="button"
      :role="multiple ? 'checkbox' : 'radio'"
      :aria-checked="isSelected(opt)"
      class="chip"
      :class="isSelected(opt) ? 'selected font-h3-semibold' : 'font-h3-regular'"
      @click="toggle(opt)"
    >
      {{ opt }}
    </button>
  </div>
</template>

<style scoped>
.el-seg-02 {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
  width: 100%;
}
.chip {
  min-width: 80px;
  min-height: 48px;
  padding: 0 20px;
  border-radius: 24px;
  border: 1px solid var(--color-grey-300);
  background: var(--background-color);
  color: var(--text-primary);
}
.chip.selected {
  background: var(--color-primary-700);
  border-color: var(--color-primary-700);
  color: var(--color-white);
}
</style>
