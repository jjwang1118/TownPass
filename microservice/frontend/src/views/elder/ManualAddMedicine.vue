<script setup lang="ts">
/**
 * EL-PG-14 長者：手動新增藥品（可連續新增多個）
 * 「加入這個藥」→「已輸入」彈窗（列出已輸入的藥）
 *   ├ 「再加一個藥」→ 清空表單，繼續輸入下一個
 *   └ 「確認」→ EL-PG-07 確認藥單
 * 從確認藥單頁「再新增一個藥」進來時，新增的藥會接在原本的手動藥單後面。
 */
import { computed, ref } from 'vue'
import { useRouter } from 'vue-router'
import PageLayout from '@/components/PageLayout.vue'
import InfoNotice from '@/components/alerts/InfoNotice.vue'
import MedicineAddedDialog from '@/components/overlays/MedicineAddedDialog.vue'
import MedicineForm from '@/views/shared/MedicineForm.vue'
import type { MedicineFormValue } from '@/types'
import { addManualMedicine, startDraftFromManual, state } from '@/store'

const router = useRouter()

const REVIEW_PATH = '/elder/add/review'
/** 是否從確認藥單頁進來（新增的藥接在原本的手動藥單後面） */
const fromReview = window.history.state?.back === REVIEW_PATH && !!state.draft?.manual

const initial: MedicineFormValue = { name: '', effect: '', amount: 1, slots: ['morning'], meal: '飯後', quantity: 0 }
const added = ref<MedicineFormValue | null>(null)
/** 每次「再加一個藥」換一個 key，讓表單重設 */
const formKey = ref(0)

/** 彈窗中列出：已暫存的藥＋剛輸入的這一個 */
const dialogList = computed<MedicineFormValue[]>(() =>
  added.value ? [...state.manualMedicines, added.value] : [...state.manualMedicines],
)

function addMore() {
  if (!added.value) return
  addManualMedicine(added.value)
  added.value = null
  formKey.value += 1
  window.scrollTo({ top: 0 })
}

function confirm() {
  if (!added.value) return
  startDraftFromManual(added.value, fromReview)
  added.value = null
  if (fromReview) router.back()
  else router.replace(REVIEW_PATH)
}
</script>

<template>
  <PageLayout title="手動新增" fallback="/elder/add/photo">
    <h2 class="page-heading">手動新增藥品</h2>
    <InfoNotice>拍照讀不到也沒關係，可以自己輸入。藥名請從清單選，避免打錯字。</InfoNotice>
    <p v-if="state.manualMedicines.length" class="pending font-h3-semibold" role="status">
      已輸入 {{ state.manualMedicines.length }} 個藥，請繼續輸入下一個
    </p>
    <MedicineForm :key="formKey" :initial="initial" submit-text="加入這個藥" @submit="(v) => (added = v)" />
    <MedicineAddedDialog
      :open="added !== null"
      :medicines="dialogList"
      @close="added = null"
      @confirm="confirm"
      @more="addMore"
    />
  </PageLayout>
</template>

<style scoped>
.pending {
  color: var(--color-primary-700);
}
</style>
