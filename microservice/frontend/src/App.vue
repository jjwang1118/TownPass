<script setup lang="ts">
import { useReminders } from '@/composables/useReminders'
import { state } from '@/store'

// 長者端用藥（9:00、12:00、18:00、22:00）與回診（前 1 小時）提醒
useReminders()

const retry = () => window.location.reload()
</script>

<template>
  <div v-if="state.apiError" class="api-error" role="alert">
    <span>{{ state.apiError }}</span>
    <button type="button" class="retry" @click="retry">重新連線</button>
  </div>
  <RouterView />
</template>

<style scoped>
.api-error {
  position: sticky;
  top: 0;
  z-index: 100;
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
  padding: 12px 16px;
  background: #fdecea;
  color: #8a1c13;
  font-size: var(--font-h3-size, 16px);
  line-height: 1.5;
}
.retry {
  min-width: 48px;
  min-height: 48px;
  padding: 0 12px;
  border: 1px solid currentColor;
  border-radius: 8px;
  background: transparent;
  color: inherit;
  font: inherit;
  font-weight: 700;
}
</style>
