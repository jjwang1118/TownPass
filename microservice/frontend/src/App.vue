<script setup lang="ts">
import { useReminders } from '@/composables/useReminders'

// 長者端用藥（9:00、12:00、18:00、22:00）與回診（前 1 小時）提醒
useReminders()
</script>

<template>
  <RouterView />
</template>
