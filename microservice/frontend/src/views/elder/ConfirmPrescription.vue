<script setup lang="ts">
/**
 * EL-PG-08 長者：資料確認（已全部核對）
 * 「確認無誤，加入藥單」→ 送到後端（配字母、記錄核對者）→ EL-PG-19 藥單加入完成（Figma E07）。
 */
import { ref } from 'vue'
import { useRouter } from 'vue-router'
import PrescriptionReview from '@/views/shared/PrescriptionReview.vue'
import { ApiError } from '@/api/client'
import { commitDraft } from '@/store'

const router = useRouter()
const submitting = ref(false)
const error = ref('')

async function submit() {
  if (submitting.value) return
  submitting.value = true
  error.value = ''
  try {
    const created = await commitDraft()
    // EL-PG-19 藥單加入完成（Figma E07）
    router.replace(created ? `/elder/add/done/${created.prescription.id}` : '/elder')
  } catch (e) {
    // 連不到伺服器由畫面上方的提示顯示；其他原因（例如後端驗證失敗）顯示在加入按鈕上方
    if (e instanceof ApiError && e.code === 'NETWORK') return
    error.value = e instanceof ApiError && e.code === 'DAYS_REQUIRED'
      ? '有藥品還沒填總顆數。請點那個藥品，填寫「總共幾顆（藥袋上的數量）」後再加入。'
      : e instanceof Error ? e.message : '加入藥單失敗，請再試一次。'
  } finally {
    submitting.value = false
  }
}
</script>

<template>
  <PrescriptionReview mode="confirm" :error="error" @submit="submit" />
</template>
