<script setup lang="ts">
/**
 * EL-PG-05 長者：拍藥袋（拍照模式）
 * 拍照 → 辨識（後端尚未建立，使用模擬辨識結果，並併入 EL-PG-14 手動新增的藥品）→ EL-PG-07
 */
import { useRouter } from 'vue-router'
import PageLayout from '@/components/PageLayout.vue'
import PhotoCamera from '@/components/cards/PhotoCamera.vue'
import SecondaryButton from '@/components/buttons/SecondaryButton.vue'
import { startDraftFromRecognition } from '@/store'

const router = useRouter()

function capture() {
  startDraftFromRecognition()
  router.push('/elder/add/review')
}
</script>

<template>
  <PageLayout title="拍藥袋" fallback="/elder/add">
    <PhotoCamera @capture="capture" />
    <SecondaryButton @click="router.push('/elder/add/manual')">改用手動輸入</SecondaryButton>
  </PageLayout>
</template>
