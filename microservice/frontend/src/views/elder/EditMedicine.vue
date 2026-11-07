<script setup lang="ts">
/** EL-PG-13 長者：修改藥品；儲存 → 回到進入前的 EL-PG-07／EL-PG-08 */
import { computed, onMounted } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import PageLayout from '@/components/PageLayout.vue'
import InfoNotice from '@/components/alerts/InfoNotice.vue'
import RxBadge from '@/components/cards/RxBadge.vue'
import MedicineForm from '@/views/shared/MedicineForm.vue'
import type { MedicineFormValue } from '@/types'
import { state, updateDraftMedicine } from '@/store'

const route = useRoute()
const router = useRouter()

const index = computed(() => Number(route.params.index))
const medicine = computed(() => state.draft?.medicines[index.value])

function goBack() {
  if (window.history.state?.back) router.back()
  else router.replace('/elder/add/review')
}

function save(value: MedicineFormValue) {
  updateDraftMedicine(index.value, value)
  goBack()
}

onMounted(() => {
  if (!medicine.value) router.replace('/elder/add')
})
</script>

<template>
  <PageLayout title="修改藥品" fallback="/elder/add/review">
    <template v-if="medicine">
      <div class="target">
        <RxBadge :code="medicine.code" />
        <h2 class="page-heading">修改這個藥</h2>
      </div>
      <InfoNotice>藥名請從清單選擇，避免打錯字。</InfoNotice>
      <MedicineForm :initial="medicine" submit-text="儲存修改" @submit="save" />
    </template>
  </PageLayout>
</template>

<style scoped>
.target {
  display: flex;
  align-items: center;
  gap: 12px;
}
</style>
