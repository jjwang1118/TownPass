<script setup lang="ts">
/** CM-ALT-03 提醒框（警示） */
import NoticeBox from './NoticeBox.vue'

defineProps<{ live?: boolean }>()
</script>

<template>
  <NoticeBox variant="warning" :live="live"><slot /></NoticeBox>
</template>
