<script setup lang="ts">
/** CM-INP-01 文字輸入框（必填紅點、Help Text、錯誤狀態） */
import { computed, useId } from 'vue'

const props = withDefaults(
  defineProps<{
    label: string
    required?: boolean
    placeholder?: string
    helpText?: string
    errorText?: string
    type?: 'text' | 'password' | 'tel'
    inputmode?: 'text' | 'numeric' | 'tel' | 'search'
    autocomplete?: string
    maxlength?: number
  }>(),
  { required: false, type: 'text', inputmode: 'text', autocomplete: 'off' },
)
const model = defineModel<string>({ required: true })

const id = useId()
const descId = computed(() => (props.errorText || props.helpText ? `${id}-desc` : undefined))
</script>

<template>
  <div class="cm-inp-01" :class="{ error: !!errorText }">
    <label :for="id" class="label-row">
      <span v-if="required" class="mandatory" aria-hidden="true" />
      <span class="label font-h3-semibold">{{ label }}</span>
      <span v-if="required" class="sr-only">（必填）</span>
    </label>
    <input
      :id="id"
      v-model="model"
      class="input font-h3-regular"
      :type="type"
      :inputmode="inputmode"
      :autocomplete="autocomplete"
      :placeholder="placeholder"
      :maxlength="maxlength"
      :required="required"
      :aria-invalid="!!errorText || undefined"
      :aria-describedby="descId"
    />
    <p v-if="errorText" :id="descId" class="desc font-h3-regular" role="alert">{{ errorText }}</p>
    <p v-else-if="helpText" :id="descId" class="desc font-h3-regular">{{ helpText }}</p>
  </div>
</template>

<style scoped>
.cm-inp-01 {
  width: 100%;
  display: flex;
  flex-direction: column;
  gap: 8px;
}
.label-row {
  display: flex;
  align-items: flex-start;
  gap: 12px;
  position: relative;
}
.mandatory {
  position: absolute;
  left: -10px;
  top: 2px;
  width: 6px;
  height: 6px;
  border-radius: 3px;
  background: var(--alarm-red-500);
}
.label {
  color: var(--color-grey-950);
}
.input {
  width: 100%;
  min-height: 48px;
  padding: 0 16px;
  border-radius: 10px;
  border: 1px solid transparent;
  background: var(--color-grey-50);
  color: var(--text-primary);
}
.input::placeholder {
  color: var(--color-grey-400);
}
.desc {
  color: var(--color-grey-950);
}
.error .input {
  border-color: var(--alarm-red-500);
}
.error .desc {
  color: var(--alarm-red-500);
}
</style>
