<script setup lang="ts">
/** EL-PG-04 長者：新增藥單 */
import { useRouter } from 'vue-router'
import PageLayout from '@/components/PageLayout.vue'
import FeatureEntry from '@/components/cards/FeatureEntry.vue'

const router = useRouter()
</script>

<template>
  <PageLayout title="新增藥單" fallback="/elder">
    <h2 class="page-heading">請藥師或家人幫忙</h2>
    <p class="page-desc">把手機交給藥師或家人，請他們幫您操作。</p>
    <FeatureEntry
      icon="camera"
      title="拍藥袋照片"
      subtitle="電腦會幫您整理藥袋內容"
      @click="router.push('/elder/add/photo')"
    />
    <FeatureEntry
      icon="qrcode"
      title="掃描藥袋 QR Code"
      subtitle="藥袋上有 QR Code 時使用（需醫院合作）"
      @click="router.push('/elder/add/qr')"
    />
  </PageLayout>
</template>
