<script setup lang="ts">
/** EL-CRD-06 相機拍照區，可從相簿選擇藥袋照片並預覽。 */
import { onBeforeUnmount, ref } from 'vue'
import AppIcon from '@/components/AppIcon.vue'
import CameraArea from './CameraArea.vue'

withDefaults(defineProps<{ busy?: boolean }>(), { busy: false })
const emit = defineEmits<{ select: [file: File | null] }>()
const camera = ref<InstanceType<typeof CameraArea> | null>(null)
const fileInput = ref<HTMLInputElement | null>(null)
const previewUrl = ref('')
const error = ref('')
const capturing = ref(false)

function clearPreview() {
  if (previewUrl.value) URL.revokeObjectURL(previewUrl.value)
  previewUrl.value = ''
}

function pickPhoto() {
  fileInput.value?.click()
}

function selectPhoto(file: File) {
  error.value = ''
  clearPreview()
  previewUrl.value = URL.createObjectURL(file)
  emit('select', file)
}

async function capturePhoto() {
  if (capturing.value) return
  const video = camera.value?.video
  if (!video?.videoWidth || !video.videoHeight) {
    error.value = '相機尚未準備好，請稍候或從相簿選擇照片。'
    return
  }
  capturing.value = true
  try {
    const canvas = document.createElement('canvas')
    canvas.width = video.videoWidth
    canvas.height = video.videoHeight
    const context = canvas.getContext('2d')
    if (!context) throw new Error('相機畫面無法讀取，請改從相簿選擇照片。')
    context.drawImage(video, 0, 0)
    const blob = await new Promise<Blob>((resolve, reject) => {
      canvas.toBlob((image) => image ? resolve(image) : reject(new Error('拍照失敗，請再試一次。')), 'image/jpeg', 0.92)
    })
    selectPhoto(new File([blob], 'prescription.jpg', { type: 'image/jpeg' }))
  } catch (e) {
    error.value = e instanceof Error ? e.message : '拍照失敗，請再試一次。'
  } finally {
    capturing.value = false
  }
}

function onFileChange(event: Event) {
  const input = event.target as HTMLInputElement
  const file = input.files?.[0]
  input.value = ''
  if (!file) return
  if (file.type && !file.type.startsWith('image/')) {
    error.value = '請選擇照片檔案。'
    return
  }
  selectPhoto(file)
}

function onPreviewError() {
  clearPreview()
  emit('select', null)
  error.value = '這張照片無法顯示，請從相簿重新選擇照片。'
}

function returnToCamera() {
  error.value = ''
  clearPreview()
  emit('select', null)
}

onBeforeUnmount(clearPreview)
</script>

<template>
  <CameraArea v-if="!previewUrl" ref="camera" hint="把藥袋放平，對準框框" :frame-height="300">
    <template #bottom>
      <div class="camera-controls">
        <button type="button" class="gallery-button" aria-label="開啟相簿，選擇藥袋照片" :disabled="busy || capturing" @click="pickPhoto">
          <AppIcon name="gallery" :size="32" />
          <span class="font-h3-regular">相簿</span>
        </button>
        <button type="button" class="shutter" aria-label="拍照" :disabled="busy || capturing" @click="capturePhoto" />
      </div>
    </template>
  </CameraArea>
  <section v-else class="photo-preview" aria-label="藥袋照片預覽">
    <img :src="previewUrl" alt="已選擇的藥袋照片" class="preview" @error="onPreviewError" />
    <p class="preview-hint font-h3-regular" role="status">已選擇藥袋照片</p>
    <div class="camera-controls">
      <button type="button" class="gallery-button" aria-label="從相簿重新選擇照片" :disabled="busy" @click="pickPhoto">
        <AppIcon name="gallery" :size="32" />
        <span class="font-h3-regular">相簿</span>
      </button>
      <button type="button" class="retake-button" aria-label="返回拍照" :disabled="busy" @click="returnToCamera">
        <AppIcon name="camera" :size="32" />
        <span class="font-h3-regular">拍照</span>
      </button>
    </div>
  </section>
  <input ref="fileInput" type="file" accept="image/*" :disabled="busy || capturing" hidden @change="onFileChange" />
  <p v-if="error" class="photo-error font-h3-regular" role="alert">{{ error }}</p>
</template>

<style scoped>
.camera-controls {
  display: grid;
  grid-template-columns: minmax(0, 1fr) 72px minmax(0, 1fr);
  align-items: center;
  gap: 16px;
  width: 232px;
  max-width: 100%;
}
.gallery-button,
.retake-button {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  gap: 4px;
  min-height: 72px;
  border-radius: 12px;
  background: var(--color-grey-900);
  color: var(--color-white);
}
.gallery-button {
  justify-self: start;
  width: 64px;
}
.retake-button {
  width: 72px;
}
.camera-controls button:disabled {
  opacity: 0.5;
}
.shutter {
  width: 72px;
  height: 72px;
  border-radius: 36px;
  background: var(--background-color);
  border: 4px solid var(--color-primary-300);
}
.photo-preview {
  flex: 1 1 auto;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  gap: 24px;
  min-height: 460px;
  padding: 24px 16px 32px;
  border-radius: 16px;
  background: var(--color-grey-900);
}
.preview {
  width: 100%;
  height: 260px;
  object-fit: contain;
  border-radius: 12px;
}
.preview-hint {
  color: var(--color-white);
  text-align: center;
}
.photo-error {
  color: var(--alarm-red-500);
}
</style>
