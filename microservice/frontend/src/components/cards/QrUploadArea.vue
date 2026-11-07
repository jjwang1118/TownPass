<script setup lang="ts">
/**
 * 二維碼照片上傳區（取代相機掃描區）
 * 整塊可點，點擊開啟相簿；選了照片後顯示縮圖
 */
import AppIcon from '@/components/AppIcon.vue'

withDefaults(defineProps<{ previewUrl?: string; busy?: boolean }>(), { previewUrl: '', busy: false })
const emit = defineEmits<{ pick: [] }>()
</script>

<template>
  <button
    type="button"
    class="qr-upload-area"
    :aria-label="previewUrl ? '重新選擇藥袋二維碼照片' : '上傳藥袋二維碼照片'"
    :aria-busy="busy || undefined"
    @click="emit('pick')"
  >
    <img v-if="previewUrl" :src="previewUrl" alt="已選擇的二維碼照片" class="preview" />
    <template v-else>
      <span class="icon"><AppIcon name="qrcode" :size="56" /></span>
      <span class="title font-h2-semibold">點這裡上傳藥袋二維碼照片</span>
      <span class="hint font-h3-regular">從相簿選一張清楚、二維碼完整的照片</span>
    </template>
    <span v-if="previewUrl" class="hint font-h3-regular">{{ busy ? '正在辨識照片…' : '點這裡重新選擇照片' }}</span>
  </button>
</template>

<style scoped>
.qr-upload-area {
  flex: 1 1 auto;
  width: 100%;
  min-height: 360px;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  gap: 16px;
  padding: 24px 16px;
  border-radius: 16px;
  border: 3px dashed var(--color-primary-300);
  background: var(--color-primary-50);
  text-align: center;
}
.icon {
  width: 104px;
  height: 104px;
  border-radius: 52px;
  background: var(--background-color);
  color: var(--color-primary-700);
  display: flex;
  align-items: center;
  justify-content: center;
}
.title {
  color: var(--color-primary-700);
}
.hint {
  color: var(--text-second);
}
.preview {
  width: 260px;
  max-width: 100%;
  aspect-ratio: 1 / 1;
  object-fit: contain;
  border-radius: 12px;
  background: var(--background-color);
}
</style>
