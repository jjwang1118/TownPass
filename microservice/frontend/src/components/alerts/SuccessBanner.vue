<script setup lang="ts">
/** EL-ALT-04 成功提示 */
defineProps<{ title: string }>()
</script>

<template>
  <div class="el-alt-04" role="status">
    <svg width="100" height="100" viewBox="0 0 100 100" aria-hidden="true" focusable="false">
      <circle cx="50" cy="50" r="50" fill="#5AB4C5" />
      <path d="M30 51l13 13 27-28" fill="none" stroke="#FFFFFF" stroke-width="8" stroke-linecap="round" stroke-linejoin="round" />
    </svg>
    <h2 class="title font-h2-semibold">{{ title }}</h2>
  </div>
</template>

<style scoped>
.el-alt-04 {
  width: 100%;
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 12px;
  padding-top: 16px;
}
.title {
  color: var(--text-primary);
  text-align: center;
}
</style>
