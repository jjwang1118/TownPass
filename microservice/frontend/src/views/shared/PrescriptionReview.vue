<script setup lang="ts">
/** 確認藥單共用版面：EL-PG-07（核對中）／EL-PG-08（資料確認） */
import { computed, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import PageLayout from '@/components/PageLayout.vue'
import PrescriptionHeader from '@/components/cards/PrescriptionHeader.vue'
import MedicineCheckCard from '@/components/cards/MedicineCheckCard.vue'
import CheckRow from '@/components/inputs/CheckRow.vue'
import WarningNotice from '@/components/alerts/WarningNotice.vue'
import PrimaryButton from '@/components/buttons/PrimaryButton.vue'
import { state } from '@/store'
import { useTts } from '@/composables/useTts'
import { medicineSpeech } from '@/utils/speech'

const props = defineProps<{ mode: 'review' | 'confirm' }>()
const emit = defineEmits<{ submit: [] }>()

const router = useRouter()
const { speak } = useTts()

const draft = computed(() => state.draft)
const unchecked = computed(() => draft.value?.medicines.filter((m) => !m.checked).length ?? 0)
const allChecked = computed(() => !!draft.value && draft.value.medicines.length > 0 && unchecked.value === 0)

const heading = computed(() => (props.mode === 'review' ? '請對照藥袋逐項核對' : '資料確認：請再看一次'))
const notice = computed(() =>
  props.mode === 'review'
    ? '這是電腦整理的結果，可能會看錯。請藥師或家人對照藥袋，全部打勾才能加入。'
    : '這是修改後的藥單。請再看一次，全部正確就按下方「確認無誤，加入藥單」。',
)
const buttonText = computed(() => (allChecked.value ? '確認無誤，加入藥單' : `還有 ${unchecked.value} 項沒核對`))

onMounted(() => {
  // 沒有草稿（例如直接開啟網址）時回到新增藥單
  if (!state.draft) router.replace('/elder/add')
})
</script>

<template>
  <PageLayout title="確認藥單" fallback="/elder/add">
    <template v-if="draft">
      <h2 class="page-heading">{{ heading }}</h2>
      <PrescriptionHeader
        :code="draft.code"
        :hospital="draft.hospital"
        :department="draft.department"
        :visit-date="draft.visitDate"
        :days="draft.days"
      />
      <WarningNotice>{{ notice }}</WarningNotice>

      <div v-for="(m, i) in draft.medicines" :key="m.code" class="item">
        <MedicineCheckCard
          :id="`med-${m.code}`"
          :medicine="m"
          @edit="router.push(`/elder/add/medicine/${i}`)"
          @speak="speak(medicineSpeech(m, true), state.lang)"
        />
        <CheckRow v-model="m.checked" :described-by="`med-${m.code}`">核對無誤</CheckRow>
      </div>

      <p class="hint font-h3-regular">讀錯了？點藥品就能修改</p>
      <PrimaryButton :disabled="!allChecked" @click="emit('submit')">{{ buttonText }}</PrimaryButton>
    </template>
  </PageLayout>
</template>

<style scoped>
.item {
  display: flex;
  flex-direction: column;
  gap: 4px;
}
.hint {
  color: var(--color-primary-700);
  text-align: center;
}
</style>
