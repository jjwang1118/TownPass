<script setup lang="ts">
/**
 * EL-PG-06 長者：掃描藥袋 QR Code
 * - App 內：開啟 App 內建 qr_code_scan，掃描成功自動跳轉
 * - 瀏覽器：相機畫面＋BarcodeDetector 自動辨識
 * - 也可以「上傳 QR Code 照片」，從照片辨識（找不到時提示換一張）
 */
import { onMounted, ref } from 'vue'
import { useRouter } from 'vue-router'
import PageLayout from '@/components/PageLayout.vue'
import QrScanCamera from '@/components/cards/QrScanCamera.vue'
import SecondaryButton from '@/components/buttons/SecondaryButton.vue'
import { isInApp, scanQrCode } from '@/composables/flutterBridge'
import { startDraftFromRecognition } from '@/store'
import { parsePrescriptionQr } from '@/utils/qr'
import { decodeQrFromFile } from '@/utils/qrImage'

const router = useRouter()

const fileInput = ref<HTMLInputElement | null>(null)
const uploading = ref(false)
const uploadError = ref('')

function onDetected(raw: string) {
  startDraftFromRecognition(parsePrescriptionQr(raw))
  router.replace('/elder/add/review')
}

function pickPhoto() {
  uploadError.value = ''
  fileInput.value?.click()
}

async function onFileChange(event: Event) {
  const input = event.target as HTMLInputElement
  const file = input.files?.[0]
  input.value = '' // 讓同一張照片可以再選一次
  if (!file) return
  uploading.value = true
  uploadError.value = ''
  try {
    const raw = await decodeQrFromFile(file)
    if (raw) onDetected(raw)
    else uploadError.value = '這張照片裡找不到 QR Code，請換一張清楚、QR Code 完整的照片。'
  } catch {
    uploadError.value = '照片無法讀取，請換一張照片再試一次。'
  } finally {
    uploading.value = false
  }
}

onMounted(async () => {
  if (!isInApp()) return
  const raw = await scanQrCode()
  if (raw && router.currentRoute.value.path === '/elder/add/qr') onDetected(raw)
})
</script>

<template>
  <PageLayout title="掃描 QR Code" fallback="/elder/add">
    <QrScanCamera @detected="onDetected" />

    <input
      ref="fileInput"
      class="sr-only"
      type="file"
      accept="image/*"
      tabindex="-1"
      aria-hidden="true"
      @change="onFileChange"
    />
    <SecondaryButton @click="pickPhoto">
      {{ uploading ? '正在辨識照片…' : '上傳 QR Code 照片' }}
    </SecondaryButton>
    <p v-if="uploadError" class="error font-h3-regular" role="alert">{{ uploadError }}</p>

    <SecondaryButton @click="router.replace('/elder/add/photo')">改用拍照</SecondaryButton>
  </PageLayout>
</template>

<style scoped>
.error {
  color: var(--alarm-red-500);
}
</style>
