<script setup lang="ts">
/**
 * EL-PG-06 長者：上傳藥袋 QR Code 照片（相機掃描暫停）
 * - 藥單 JSON 交給既有後端解析，保留健保藥品比對與同成分警示
 * - 網址型二維碼先呼叫 OCR 服務，再將藥單 JSON 送後端預覽
 * - 成功進入確認藥單；失敗顯示原因與實際讀到的內容
 */
import { onBeforeUnmount, onMounted, ref } from 'vue'
import { useRouter } from 'vue-router'
import PageLayout from '@/components/PageLayout.vue'
import QrScanCamera, { type ScanFailReason } from '@/components/cards/QrScanCamera.vue'
import QrUploadArea from '@/components/cards/QrUploadArea.vue'
import SecondaryButton from '@/components/buttons/SecondaryButton.vue'
import { isInApp, scanQrCode } from '@/composables/flutterBridge'
import { startDraftFromQr } from '@/store'
import { ApiError } from '@/api/client'
import { decodeQrFromFile } from '@/utils/qrImage'
import { PrescriptionOcrError, isUrl, recognizePrescriptionFromUrl } from '@/services/prescriptionOcr'

const router = useRouter()

/**
 * 是否使用相機掃描（網頁相機＋App 內建掃描器）
 * 目前先不用相機，改以「上傳照片」辨識二維碼；要恢復相機掃描時改成 true
 */
const USE_CAMERA = false

const fileInput = ref<HTMLInputElement | null>(null)
const uploading = ref(false)
/** 已選擇照片的縮圖網址 */
const previewUrl = ref('')

/** 掃描失敗提示：原因說明＋（若有）實際讀到的內容 */
interface ScanFailure {
  message: string
  raw?: string
}
const failure = ref<ScanFailure | null>(null)

function fail(message: string, raw?: string) {
  failure.value = { message, raw }
}

/** 辨識或後端預覽處理中，避免重複送出 */
const reading = ref(false)

/** JSON 交給既有後端解析；網址先做 OCR，再將結果送後端預覽與同成分比對。 */
async function onDetected(raw: string) {
  if (reading.value) return
  failure.value = null
  reading.value = true
  try {
    const json = isUrl(raw) ? await recognizePrescriptionFromUrl(raw) : raw
    await startDraftFromQr(json)
    failure.value = null
    await router.replace('/elder/add/review')
  } catch (e) {
    if (e instanceof ApiError && e.code === 'QR_INVALID') {
      fail(`${e.message}。請重新掃描，或上傳正確的照片。`, raw)
    } else if (e instanceof PrescriptionOcrError) {
      fail(`${e.message}。`, raw)
    } else {
      fail(e instanceof Error ? e.message : '掃描失敗，請再試一次。', raw)
    }
  } finally {
    reading.value = false
  }
}

function onCameraFailed(reason: ScanFailReason) {
  if (reason === 'unsupported') {
    fail('這個瀏覽器無法用相機掃描二維碼，請改用「上傳 QR Code 照片」。')
  } else if (!failure.value) {
    fail('找不到二維碼。請把二維碼放進框框、靠近一點，或改用「上傳 QR Code 照片」。')
  }
}

function pickPhoto() {
  fileInput.value?.click()
}

async function onFileChange(event: Event) {
  const input = event.target as HTMLInputElement
  const file = input.files?.[0]
  input.value = '' // 讓同一張照片可以再選一次
  if (!file) return
  if (previewUrl.value) URL.revokeObjectURL(previewUrl.value)
  previewUrl.value = URL.createObjectURL(file)
  failure.value = null
  uploading.value = true
  try {
    const raw = await decodeQrFromFile(file)
    if (raw) await onDetected(raw)
    else fail('這張照片裡找不到二維碼，請換一張清楚、二維碼完整的照片。')
  } catch {
    fail('照片無法讀取，請換一張照片再試一次。')
  } finally {
    uploading.value = false
  }
}

onBeforeUnmount(() => {
  if (previewUrl.value) URL.revokeObjectURL(previewUrl.value)
})

onMounted(async () => {
  if (!USE_CAMERA || !isInApp()) return
  const raw = await scanQrCode()
  if (router.currentRoute.value.path !== '/elder/add/qr') return
  if (raw) onDetected(raw)
  else fail('沒有掃到二維碼，請再試一次，或改用「上傳 QR Code 照片」。')
})
</script>

<template>
  <PageLayout title="掃描 QR Code" fallback="/elder/add">
    <QrScanCamera v-if="USE_CAMERA" @detected="onDetected" @failed="onCameraFailed" />
    <QrUploadArea v-else :preview-url="previewUrl" :busy="uploading || reading" @pick="pickPhoto" />

    <p v-if="reading" class="reading font-h3-semibold" role="status">正在讀取藥單，請稍候…</p>

    <div v-if="failure" class="scan-failed" role="alert">
      <p class="title font-h3-semibold">掃描失敗</p>
      <p class="font-h3-regular">{{ failure.message }}</p>
      <p v-if="failure.raw" class="raw font-h3-regular">讀到的內容：{{ failure.raw }}</p>
    </div>

    <input
      ref="fileInput"
      class="sr-only"
      type="file"
      accept="image/*"
      tabindex="-1"
      aria-hidden="true"
      @change="onFileChange"
    />
    <SecondaryButton v-if="USE_CAMERA" @click="pickPhoto">
      {{ uploading ? '正在辨識照片…' : '上傳 QR Code 照片' }}
    </SecondaryButton>

    <SecondaryButton @click="router.replace('/elder/add/photo')">改用拍照</SecondaryButton>
  </PageLayout>
</template>

<style scoped>
.reading {
  padding: 12px 16px;
  border-radius: 8px;
  background: var(--color-primary-50);
  border: 1px solid var(--color-primary-300);
  color: var(--color-primary-700);
}
.scan-failed {
  display: flex;
  flex-direction: column;
  gap: 4px;
  padding: 12px 16px;
  border-radius: 8px;
  border: 2px solid var(--alarm-red-500);
  background: var(--background-color);
  color: var(--alarm-red-500);
}
.scan-failed .title {
  font-size: var(--font-title-size);
}
.scan-failed .raw {
  color: var(--text-second);
  overflow-wrap: anywhere;
}
</style>
