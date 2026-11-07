<script setup lang="ts">
/** EL-PG-15 長者：緊急醫療卡（第一次為空，按「填寫醫療卡」開始填） */
import { computed } from 'vue'
import { useRouter } from 'vue-router'
import EmergencyCardView from '@/views/shared/EmergencyCardView.vue'
import PrimaryButton from '@/components/buttons/PrimaryButton.vue'
import { state } from '@/store'
import { isCardEmpty } from '@/utils/card'

const router = useRouter()
const notices = computed(() => [
  '只有綁定的家屬和經過驗證的救護人員看得到。',
  '慢性病、過敏由您自己填寫；目前用藥來自您在本服務建立的藥單。',
  ...(state.cardCode ? [`救護人員用卡號 ${state.cardCode} 查詢，請貼在敬老卡背面。`] : []),
])
const buttonText = computed(() => (isCardEmpty(state.card) ? '填寫醫療卡' : '編輯醫療卡'))
</script>

<template>
  <EmergencyCardView viewer="elder" :notices="notices" fallback="/elder">
    <PrimaryButton @click="router.push('/elder/card/edit')">{{ buttonText }}</PrimaryButton>
  </EmergencyCardView>
</template>
