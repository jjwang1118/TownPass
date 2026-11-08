<script setup lang="ts">
/**
 * EL-PG-05：拍照或相簿選圖 → 確認照片 → 裝置端 OCR → 後端預覽 → 藥單核對。
 */
import { onBeforeUnmount, ref, shallowRef } from 'vue'
import { useRouter } from 'vue-router'
import PageLayout from '@/components/PageLayout.vue'
import PhotoCamera from '@/components/cards/PhotoCamera.vue'
import SecondaryButton from '@/components/buttons/SecondaryButton.vue'
import PrimaryButton from '@/components/buttons/PrimaryButton.vue'
import { createPrescriptionRecognizer, type OcrProgress } from '@/services/localPrescriptionOcr'
import type { PhotoRecognitionIn } from '@/api/types'
import { startDraftFromRecognition } from '@/store'

const router = useRouter()
const selectedPhoto = shallowRef<File | null>(null)
const recognized = shallowRef<PhotoRecognitionIn | null>(null)
const busy = ref(false)
const error = ref('')
const comparing = ref(false)
const progress = ref<OcrProgress>({ percent: 0, message: '' })
let active = true
const request = new AbortController()

// 開發用：不啟動後端也能檢查裝置端 OCR 的原始文字與整理出的欄位（正式建置不顯示）。
const isDev = import.meta.env.DEV
const ocrText = ref('')
const HEADER_FIELDS = [
  ['hospital', '醫院'], ['department', '科別'], ['doctor', '醫師'], ['visit_date', '看診日'], ['days', '天數'],
] as const
const ITEM_FIELDS = [
  ['name', '藥名'], ['strength', '劑量'], ['purpose', '適應症'], ['dose_qty', '每次幾顆'],
  ['quantity', '總顆數'], ['frequency', '一天幾次'], ['meal_timing', '飯前飯後'],
] as const
const show = (value: unknown) => (value === null || value === undefined || value === '' ? '—' : String(value))
const score = (confidence: Record<string, number>, field: string) =>
  confidence[field] === undefined ? '' : `（${confidence[field].toFixed(2)}）`

const updateProgress = (next: OcrProgress) => {
  if (active) progress.value = { ...next, percent: Math.max(progress.value.percent, next.percent) }
}
const ocrEngine = ref('')
const updateText = (text: string, engine: string) => {
  if (!active || !isDev) return
  ocrText.value = text
  ocrEngine.value = engine
}
let recognizer = createPrescriptionRecognizer(updateProgress, updateText)

function selectPhoto(file: File | null) {
  selectedPhoto.value = file
  recognized.value = null
  ocrText.value = ''
  error.value = ''
  progress.value = { percent: 0, message: '' }
}

async function confirmPhoto() {
  if (!selectedPhoto.value || busy.value) return
  busy.value = true
  comparing.value = false
  error.value = ''
  progress.value = { percent: 0, message: '正在讀取照片…' }
  try {
    // 後端連線失敗時保留已辨識的欄位，重試不必再跑一次 OCR。
    if (!recognized.value) recognized.value = await recognizer.recognize(selectedPhoto.value)
    if (!active) return
    comparing.value = true
    await startDraftFromRecognition(recognized.value, request.signal)
    if (active && router.currentRoute.value.path === '/elder/add/photo') await router.push('/elder/add/review')
  } catch (e) {
    if (active) {
      error.value = e instanceof Error ? e.message : '照片辨識失敗，請重新選擇照片後再試一次。'
      if (!recognized.value) {
        recognizer.dispose()
        recognizer = createPrescriptionRecognizer(updateProgress, updateText)
      }
    }
  } finally {
    if (active) busy.value = false
  }
}

onBeforeUnmount(() => {
  active = false
  request.abort()
  recognizer.dispose()
})
</script>

<template>
  <PageLayout title="拍藥袋" fallback="/elder/add">
    <PhotoCamera :busy="busy" @select="selectPhoto" />
    <div v-if="busy" class="recognizing" role="status" aria-live="polite">
      <p class="font-h3-regular">{{ comparing ? '正在比對藥品資料…' : progress.message }}</p>
      <progress :value="comparing ? undefined : progress.percent" max="100" aria-label="照片辨識進度" />
    </div>
    <p v-if="error" class="photo-error font-h3-regular" role="alert">{{ error }}</p>
    <PrimaryButton v-if="selectedPhoto" :disabled="busy" @click="confirmPhoto">
      {{ busy ? '正在處理，請稍候…' : recognized ? '重新送出藥單' : '確認並辨識' }}
    </PrimaryButton>
    <SecondaryButton @click="router.push('/elder/add/manual')">改用手動輸入</SecondaryButton>
    <section v-if="isDev && (recognized || ocrText)" class="ocr-debug" aria-label="OCR 辨識結果（開發用）">
      <h2 class="font-h3-semibold">OCR 辨識結果（開發用）{{ ocrEngine ? `：${ocrEngine}` : '' }}</h2>
      <dl v-if="recognized">
        <template v-for="[field, label] in HEADER_FIELDS" :key="field">
          <dt>{{ label }}</dt>
          <dd>{{ show(recognized[field]) }}{{ score(recognized.confidence, field) }}</dd>
        </template>
      </dl>
      <div v-for="(item, index) in recognized?.items ?? []" :key="index" class="ocr-item">
        <h3 class="font-h3-regular">第 {{ index + 1 }} 個藥</h3>
        <dl>
          <template v-for="[field, label] in ITEM_FIELDS" :key="field">
            <dt>{{ label }}</dt>
            <dd>{{ show(item[field]) }}{{ score(item.confidence, field) }}</dd>
          </template>
        </dl>
      </div>
      <details v-if="ocrText">
        <summary>原始辨識文字</summary>
        <pre>{{ ocrText }}</pre>
      </details>
    </section>
  </PageLayout>
</template>

<style scoped>
.recognizing {
  display: flex;
  flex-direction: column;
  gap: 8px;
  color: var(--text-second);
}
.recognizing progress {
  width: 100%;
  accent-color: var(--color-primary-500);
}
.photo-error {
  color: var(--alarm-red-500);
}
.ocr-debug {
  display: flex;
  flex-direction: column;
  gap: 12px;
  padding: 16px;
  border: 2px dashed var(--color-grey-300);
  border-radius: 12px;
  font-size: 16px;
}
.ocr-debug dl {
  display: grid;
  grid-template-columns: max-content minmax(0, 1fr);
  gap: 4px 12px;
  margin: 0;
}
.ocr-debug dt {
  color: var(--text-second);
}
.ocr-debug dd {
  margin: 0;
  overflow-wrap: anywhere;
}
.ocr-debug summary {
  min-height: 48px;
  display: flex;
  align-items: center;
  cursor: pointer;
}
.ocr-debug pre {
  margin: 0;
  white-space: pre-wrap;
  overflow-wrap: anywhere;
  font-size: 14px;
}
</style>
