<script setup lang="ts">
/** RE-PG-04 救護人員：頁面已自動關閉 */
import { useRouter } from 'vue-router'
import PageLayout from '@/components/PageLayout.vue'
import AppIcon from '@/components/AppIcon.vue'
import PrimaryButton from '@/components/buttons/PrimaryButton.vue'

const router = useRouter()
const again = () => router.replace('/rescue/search')
</script>

<template>
  <PageLayout title="查詢緊急醫療卡" :on-back="again">
    <section class="closed" role="status">
      <span class="icon"><AppIcon name="clock" :size="48" /></span>
      <h2 class="page-heading">頁面已自動關閉</h2>
      <p class="page-desc">為保護長者隱私，查詢結果 30 分鐘後會自動關閉。需要再次查看，請重新查詢。</p>
    </section>
    <div class="flex-spacer" />
    <PrimaryButton @click="again">重新查詢</PrimaryButton>
  </PageLayout>
</template>

<style scoped>
.closed {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 12px;
  text-align: center;
  padding-top: 32px;
}
.icon {
  width: 96px;
  height: 96px;
  border-radius: 48px;
  background: var(--color-grey-50);
  color: var(--text-second);
  display: flex;
  align-items: center;
  justify-content: center;
}
</style>
