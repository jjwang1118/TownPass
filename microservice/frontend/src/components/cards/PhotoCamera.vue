<script setup lang="ts">
/** EL-CRD-06 相機拍照區 */
import CameraArea from './CameraArea.vue'

const emit = defineEmits<{ capture: [] }>()
</script>

<template>
  <CameraArea hint="把藥袋放平，對準框框" :frame-height="300">
    <template #bottom>
      <button type="button" class="shutter" aria-label="拍照" @click="emit('capture')" />
    </template>
  </CameraArea>
</template>

<style scoped>
.shutter {
  width: 72px;
  height: 72px;
  border-radius: 36px;
  background: var(--background-color);
  border: 4px solid var(--color-primary-300);
}
</style>
