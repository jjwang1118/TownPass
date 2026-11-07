<script setup lang="ts">
/** FM-PG-05 家屬：長輩的緊急醫療卡（沒有編輯按鈕） */
import EmergencyCardView from '@/views/shared/EmergencyCardView.vue'

const notices = [
  '您是綁定家屬，可以查看，但不能修改。',
  '慢性病、過敏由長輩自己填寫；目前用藥來自長輩在本服務建立的藥單。',
]
</script>

<template>
  <EmergencyCardView viewer="family" :notices="notices" fallback="/family/home" />
</template>
