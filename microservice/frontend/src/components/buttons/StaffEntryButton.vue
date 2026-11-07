<script setup lang="ts">
/**
 * 員工專區入口（長者首頁最下方）：灰色框線，與長輩使用的主色按鈕區分，避免誤點
 * 點擊 → RE-PG-01 救護人員登入（確認工作人員身分）
 */
import { useRouter } from 'vue-router'
import AppIcon from '@/components/AppIcon.vue'

const router = useRouter()
</script>

<template>
  <button type="button" class="staff-entry" @click="router.push('/rescue')">
    <AppIcon name="medical-card" />
    <span class="texts">
      <span class="title font-h3-semibold">員工專區</span>
      <span class="desc font-h3-regular">救護人員查詢緊急醫療卡</span>
    </span>
    <AppIcon name="chevron-right" />
  </button>
</template>

<style scoped>
.staff-entry {
  width: 100%;
  min-height: 56px;
  margin-top: 16px;
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 8px 16px;
  border-radius: 10px;
  border: 1px dashed var(--color-grey-500);
  background: var(--color-grey-50);
  color: var(--text-second);
  text-align: left;
}
.texts {
  flex: 1 1 auto;
  display: flex;
  flex-direction: column;
}
</style>
