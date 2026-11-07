<script setup lang="ts">
/** 藥報平安 logo（logo/S），裝飾圖，隱藏於報讀器 */
withDefaults(defineProps<{ size?: number }>(), { size: 24 })
</script>

<template>
  <svg :width="size" :height="size" viewBox="0 0 24 24" aria-hidden="true" focusable="false">
    <rect width="24" height="24" rx="6" fill="#356C77" />
    <rect x="5" y="9.5" width="14" height="5" rx="2.5" fill="#FFFFFF" transform="rotate(-45 12 12)" />
    <path d="M12 12l3.5-3.5a2.5 2.5 0 013.5 3.5L15.5 15.5z" fill="#F5BA4B" transform="translate(-1.75 -1.75)" />
  </svg>
</template>
