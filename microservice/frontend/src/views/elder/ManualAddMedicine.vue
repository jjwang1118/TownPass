<script setup lang="ts">
/**
 * EL-PG-14 長者：手動新增藥品
 * 「加入這個藥」→ 顯示「已輸入」彈窗（藥品摘要）→ 按「確認」→ EL-PG-07 確認藥單（核對）
 */
import { ref } from 'vue'
import { useRouter } from 'vue-router'
import PageLayout from '@/components/PageLayout.vue'
import InfoNotice from '@/components/alerts/InfoNotice.vue'
import MedicineAddedDialog from '@/components/overlays/MedicineAddedDialog.vue'
import MedicineForm from '@/views/shared/MedicineForm.vue'
import type { MedicineFormValue } from '@/types'
import { startDraftFromManual } from '@/store'

const router = useRouter()

const initial: MedicineFormValue = { name: '', effect: '', amount: 1, slots: ['morning'], meal: '飯後' }
const added = ref<MedicineFormValue | null>(null)

function confirm() {
  if (!added.value) return
  startDraftFromManual(added.value)
  added.value = null
  router.replace('/elder/add/review')
}
</script>

<template>
  <PageLayout title="手動新增" fallback="/elder/add/photo">
    <h2 class="page-heading">手動新增藥品</h2>
    <InfoNotice>拍照讀不到也沒關係，可以自己輸入。藥名請從清單選，避免打錯字。</InfoNotice>
    <MedicineForm :initial="initial" submit-text="加入這個藥" @submit="(v) => (added = v)" />
    <MedicineAddedDialog :open="added !== null" :medicine="added" @close="added = null" @confirm="confirm" />
  </PageLayout>
</template>
