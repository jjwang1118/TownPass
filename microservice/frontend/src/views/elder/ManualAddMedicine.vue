<script setup lang="ts">
/** EL-PG-14 長者：手動新增藥品；加入 → 回到 EL-PG-05，並將藥品併入藥單 */
import { useRouter } from 'vue-router'
import PageLayout from '@/components/PageLayout.vue'
import InfoNotice from '@/components/alerts/InfoNotice.vue'
import MedicineForm from '@/views/shared/MedicineForm.vue'
import type { MedicineFormValue } from '@/types'
import { addManualMedicine } from '@/store'

const router = useRouter()

const initial: MedicineFormValue = { name: '', effect: '', amount: 1, slots: ['morning'], meal: '飯後' }

function add(value: MedicineFormValue) {
  addManualMedicine(value)
  if (window.history.state?.back) router.back()
  else router.replace('/elder/add/photo')
}
</script>

<template>
  <PageLayout title="手動新增" fallback="/elder/add/photo">
    <h2 class="page-heading">手動新增藥品</h2>
    <InfoNotice>拍照讀不到也沒關係，可以自己輸入。藥名請從清單選，避免打錯字。</InfoNotice>
    <MedicineForm :initial="initial" submit-text="加入這個藥" @submit="add" />
  </PageLayout>
</template>
