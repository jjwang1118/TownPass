<script setup lang="ts">
/**
 * EL-PG-08 長者：資料確認（已全部核對）
 * 「確認無誤，加入藥單」→ 送到後端（配字母、記錄核對者）。藥單加入完成頁（Figma E07）尚未建檔，暫回到首頁。
 */
import { ref } from 'vue'
import { useRouter } from 'vue-router'
import PrescriptionReview from '@/views/shared/PrescriptionReview.vue'
import { commitDraft } from '@/store'

const router = useRouter()
const submitting = ref(false)

async function submit() {
  if (submitting.value) return
  submitting.value = true
  try {
    await commitDraft()
    router.replace('/elder')
  } catch {
    /* 錯誤由畫面上方的提示顯示 */
  } finally {
    submitting.value = false
  }
}
</script>

<template>
  <PrescriptionReview mode="confirm" @submit="submit" />
</template>
