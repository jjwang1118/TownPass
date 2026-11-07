<script setup lang="ts">
/**
 * EL-PG-06 長者：掃描藥袋 QR Code
 * - App 內：開啟 App 內建 qr_code_scan，掃描成功自動跳轉
 * - 瀏覽器：相機畫面＋BarcodeDetector 自動辨識
 * - 也可以「上傳 QR Code 照片」，從照片辨識
 * - 無法掃描時一律顯示「掃描失敗」提示（不是藥單、照片找不到二維碼、逾時、裝置不支援、App 掃描沒有結果）
 */
import { onMounted, ref } from 'vue'
import { useRouter } from 'vue-router'
import PageLayout from '@/components/PageLayout.vue'
import QrScanCamera, { type ScanFailReason } from '@/components/cards/QrScanCamera.vue'
import SecondaryButton from '@/components/buttons/SecondaryButton.vue'
import { isInApp, scanQrCode } from '@/composables/flutterBridge'
import { startDraftFromQr } from '@/store'
import { ApiError } from '@/api/client'
import { decodeQrFromFile } from '@/utils/qrImage'

const router = useRouter()

const fileInput = ref<HTMLInputElement | null>(null)
const uploading = ref(false)

/** 掃描失敗提示：原因說明＋（若有）實際讀到的內容 */
interface ScanFailure {
  message: string
  raw?: string
}
const failure = ref<ScanFailure | null>(null)

function fail(message: string, raw?: string) {
  failure.value = { message, raw }
}

/** 交給後端解析（格式見 docs/qrcode_format.md）：會比對健保藥品資料，標示同成分的藥 */
async function onDetected(raw: string) {
  try {
    await startDraftFromQr(raw)
  } catch (e) {
    if (e instanceof ApiError && e.code === 'QR_INVALID') {
      fail(`${e.message}。請重新掃描，或上傳正確的照片。`, raw)
    } else {
      fail(e instanceof Error ? e.message : '掃描失敗，請再試一次。')
    }
    return
  }
  failure.value = null
  router.replace('/elder/add/review')
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
  uploading.value = true
  try {
    const raw = await decodeQrFromFile(file)
    if (raw) onDetected(raw)
    else fail('這張照片裡找不到二維碼，請換一張清楚、二維碼完整的照片。')
  } catch {
    fail('照片無法讀取，請換一張照片再試一次。')
  } finally {
    uploading.value = false
  }
}

onMounted(async () => {
  if (!isInApp()) return
  const raw = await scanQrCode()
  if (router.currentRoute.value.path !== '/elder/add/qr') return
  if (raw) onDetected(raw)
  else fail('沒有掃到二維碼，請再試一次，或改用「上傳 QR Code 照片」。')
})
</script>

<template>
  <PageLayout title="掃描 QR Code" fallback="/elder/add">
    <QrScanCamera @detected="onDetected" @failed="onCameraFailed" />

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
    <SecondaryButton @click="pickPhoto">
      {{ uploading ? '正在辨識照片…' : '上傳 QR Code 照片' }}
    </SecondaryButton>

    <SecondaryButton @click="router.replace('/elder/add/photo')">改用拍照</SecondaryButton>
  </PageLayout>
</template>

<style scoped>
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
