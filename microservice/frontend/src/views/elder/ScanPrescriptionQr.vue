<script setup lang="ts">
/**
 * EL-PG-06 長者：掃描藥袋 QR Code
 * - App 內：開啟 App 內建 qr_code_scan，掃描成功自動跳轉
 * - 瀏覽器：相機畫面＋BarcodeDetector 自動辨識
 * - 也可以「上傳 QR Code 照片」，從照片辨識
 * - 二維碼內容是網址時：送後端下載藥單圖片做 OCR，整理成藥單後進入確認藥單
 * - 無法掃描時一律顯示「掃描失敗」與錯誤原因（不是藥單、網址打不開、讀不出藥單、照片找不到二維碼、逾時、裝置不支援、App 掃描沒有結果）
 */
import { onBeforeUnmount, onMounted, ref } from 'vue'
import { useRouter } from 'vue-router'
import PageLayout from '@/components/PageLayout.vue'
import QrScanCamera, { type ScanFailReason } from '@/components/cards/QrScanCamera.vue'
import QrUploadArea from '@/components/cards/QrUploadArea.vue'
import SecondaryButton from '@/components/buttons/SecondaryButton.vue'
import { isInApp, scanQrCode } from '@/composables/flutterBridge'
import { startDraftFromRecognition } from '@/store'
import { parsePrescriptionQr } from '@/utils/qr'
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

/** 網址型二維碼：等待後端下載圖片＋OCR 中 */
const reading = ref(false)

/** 藥單 JSON 文字 → 建立草稿並進入確認藥單；不完整時顯示掃描失敗 */
function useRecognized(json: string, raw: string): boolean {
  const result = parsePrescriptionQr(json)
  if (!result.ok) {
    if (result.reason === 'missing') {
      fail(`藥單資料不完整，缺少：${result.missing.join('、')}。`, raw)
    }
    return false
  }
  failure.value = null
  startDraftFromRecognition(result.rx)
  router.replace('/elder/add/review')
  return true
}

/**
 * 掃到二維碼後：
 * 1. 內容是藥單 JSON → 直接建立藥單
 * 2. 內容是網址 → 後端下載圖片、OCR、整理成藥單 → 確認藥單；打不開或讀不出時顯示錯誤原因
 * 3. 其他內容 → 掃描失敗
 */
async function onDetected(raw: string) {
  if (reading.value) return
  failure.value = null // 清掉上一次的掃描失敗
  if (useRecognized(raw, raw)) return
  if (failure.value) return // 藥單 JSON 但缺欄位，已顯示原因

  if (!isUrl(raw)) {
    fail('這不是藥袋的二維碼，請重新掃描，或上傳正確的照片。', raw)
    return
  }

  reading.value = true
  failure.value = null
  try {
    const json = await recognizePrescriptionFromUrl(raw)
    if (!useRecognized(json, raw) && !failure.value) {
      fail('圖片上找不到藥單資料（藥名、用法、數量）。', raw)
    }
  } catch (e) {
    const reason = e instanceof PrescriptionOcrError ? e.message : '讀取藥單時發生錯誤'
    fail(`${reason}。`, raw)
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
