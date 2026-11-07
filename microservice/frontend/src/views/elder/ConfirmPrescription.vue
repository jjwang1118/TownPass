<script setup lang="ts">
/**
 * EL-PG-08 長者：資料確認（已全部核對）
 * 「確認無誤，加入藥單」→ 寫入藥單。藥單加入完成頁（Figma E07）尚未建檔，暫回到首頁。
 */
import { useRouter } from 'vue-router'
import PrescriptionReview from '@/views/shared/PrescriptionReview.vue'
import { commitDraft } from '@/store'

const router = useRouter()

function submit() {
  commitDraft()
  router.replace('/elder')
}
</script>

<template>
  <PrescriptionReview mode="confirm" @submit="submit" />
</template>
