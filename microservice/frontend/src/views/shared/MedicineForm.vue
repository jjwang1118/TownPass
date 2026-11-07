<script setup lang="ts">
/**
 * 藥品表單共用：EL-PG-13 修改藥品／EL-PG-14 手動新增藥品
 * - 藥名必填，須從搜尋結果點選
 * - 什麼時候吃：複選，至少 1 個；飯前飯後：單選
 */
import { computed, reactive, ref } from 'vue'
import DrugSearch from '@/components/inputs/DrugSearch.vue'
import AmountStepper from '@/components/inputs/AmountStepper.vue'
import OptionChips from '@/components/segments/OptionChips.vue'
import PrimaryButton from '@/components/buttons/PrimaryButton.vue'
import { MEAL_OPTIONS, SLOTS, SLOT_KEY_BY_NAME } from '@/data/constants'
import type { DrugEntry, MealTiming, MedicineFormValue } from '@/types'



const props = defineProps<{ initial: MedicineFormValue; submitText: string }>()
const emit = defineEmits<{ submit: [value: MedicineFormValue] }>()

const form = reactive({
  name: props.initial.name,
  effect: props.initial.effect,
  amount: props.initial.amount,
  slotNames: SLOTS.filter((s) => props.initial.slots.includes(s.key)).map((s) => s.name) as string[],
  meal: props.initial.meal as string,
})
const tried = ref(false)

const slotOptions = SLOTS.map((s) => s.name)

const nameError = computed(() => (tried.value && !form.name ? '請輸入藥名，並從清單選擇' : ''))
const slotError = computed(() => (tried.value && form.slotNames.length === 0 ? '請至少選一個時段' : ''))

function onSelect(drug: DrugEntry) {
  const keep = props.initial.name.toLowerCase().startsWith(drug.name.toLowerCase())
  form.name = keep ? props.initial.name : `${drug.name} ${drug.doses[0]}`
  form.effect = drug.effect
}

function submit() {
  tried.value = true
  if (!form.name || form.slotNames.length === 0) return
  emit('submit', {
    name: form.name,
    effect: form.effect,
    amount: form.amount,
    slots: form.slotNames.map((n) => SLOT_KEY_BY_NAME[n]),
    meal: form.meal as MealTiming,
  })
}
</script>

<template>
  <DrugSearch :selected="initial.name" :error-text="nameError" @select="onSelect" />

  <h3 id="amount-label" class="field-label font-h3-semibold">一次幾顆</h3>
  <AmountStepper v-model="form.amount" label="一次幾顆" />

  <h3 class="field-label font-h3-semibold">什麼時候吃（可以選很多個）</h3>
  <OptionChips v-model="form.slotNames" :options="slotOptions" multiple label="什麼時候吃" required />
  <p v-if="slotError" class="error font-h3-regular" role="alert">{{ slotError }}</p>

  <h3 class="field-label font-h3-semibold">飯前還是飯後</h3>
  <OptionChips v-model="form.meal" :options="MEAL_OPTIONS" label="飯前還是飯後" />

  <PrimaryButton @click="submit">{{ submitText }}</PrimaryButton>
</template>

<style scoped>
.field-label {
  color: var(--color-grey-950);
}
.error {
  color: var(--alarm-red-500);
}
</style>
