<script setup lang="ts">
/**
 * EL-PG-05 長者：拍藥袋
 * 拍照（或從相簿選照片）→ 手機上用 Tesseract 辨識藥袋上的字（services/bagOcr.ts，裝置端推論）
 * → 後端 ocr-preview 整理成藥單、比對健保藥品資料，並併入 EL-PG-14 手動新增的藥品 → EL-PG-07 確認藥單
 *
 * 和 QR 頁一樣用 <input type="file"> 取得照片（不在網頁裡開相機預覽）：
 * 在城市通 App 裡會開系統相機或相簿，一般瀏覽器可選電腦裡的照片測試。
 */
import { onBeforeUnmount, onMounted, ref } from 'vue'
import { useRouter } from 'vue-router'
import PageLayout from '@/components/PageLayout.vue'
import PrimaryButton from '@/components/buttons/PrimaryButton.vue'
import SecondaryButton from '@/components/buttons/SecondaryButton.vue'
import { ApiError } from '@/api/client'
import { recognizeBagLines, releaseBagOcr, warmUpBagOcr } from '@/services/bagOcr'
import { startDraftFromOcr } from '@/store'

const router = useRouter()

const cameraInput = ref<HTMLInputElement | null>(null)
const albumInput = ref<HTMLInputElement | null>(null)
const previewUrl = ref('')
/** 'reading'：辨識照片上的字；'sending'：後端整理藥單 */
const step = ref<'idle' | 'reading' | 'sending'>('idle')
const percent = ref(0)

interface Failure {
  message: string
  lines?: string[]
}
const failure = ref<Failure | null>(null)

function pick(input: HTMLInputElement | null) {
  if (step.value === 'idle') input?.click()
}

async function onFileChange(event: Event) {
  const input = event.target as HTMLInputElement
  const file = input.files?.[0]
  input.value = '' // 讓同一張照片可以再選一次
  if (!file) return
  if (previewUrl.value) URL.revokeObjectURL(previewUrl.value)
  previewUrl.value = URL.createObjectURL(file)
  failure.value = null
  percent.value = 0

  let lines: string[] = []
  step.value = 'reading'
  try {
    lines = await recognizeBagLines(file, (ratio) => (percent.value = Math.round(ratio * 100)))
    if (lines.length === 0) {
      failure.value = { message: '照片上看不到字。請把藥袋放平、靠近一點、光線充足，再拍一次。' }
      return
    }
    step.value = 'sending'
    await startDraftFromOcr(lines)
    await router.push('/elder/add/review')
  } catch (e) {
    if (e instanceof ApiError && ['OCR_EMPTY', 'OCR_UNREADABLE'].includes(e.code)) {
      failure.value = { message: `${e.message}。也可以改用掃 QR Code 或手動輸入。`, lines }
    } else if (e instanceof ApiError) {
      failure.value = { message: e.message, lines }
    } else {
      failure.value = { message: '照片無法辨識，請換一張照片再試一次。' }
    }
  } finally {
    step.value = 'idle'
  }
}

onMounted(warmUpBagOcr)
onBeforeUnmount(() => {
  if (previewUrl.value) URL.revokeObjectURL(previewUrl.value)
  void releaseBagOcr()
})
</script>

<template>
  <PageLayout title="拍藥袋" fallback="/elder/add">
    <div class="photo-area">
      <img v-if="previewUrl" :src="previewUrl" alt="剛拍的藥袋照片" class="preview" />
      <template v-else>
        <p class="title font-h2-semibold">把藥袋放平，拍下有藥名和用法的那一面</p>
        <p class="hint font-h3-regular">光線要充足，字要清楚、不要反光</p>
      </template>
    </div>

    <p v-if="step !== 'idle'" class="reading font-h3-semibold" role="status" aria-live="polite">
      {{ step === 'reading' ? `正在讀藥袋上的字…（${percent}%）` : '正在整理藥單，請稍候…' }}
    </p>

    <div v-if="failure" class="failed" role="alert">
      <p class="title font-h3-semibold">辨識失敗</p>
      <p class="font-h3-regular">{{ failure.message }}</p>
      <p v-if="failure.lines?.length" class="lines font-h3-regular">讀到的字：{{ failure.lines.join(' ／ ') }}</p>
    </div>

    <PrimaryButton :disabled="step !== 'idle'" @click="pick(cameraInput)">拍藥袋照片</PrimaryButton>
    <SecondaryButton @click="pick(albumInput)">從相簿選照片</SecondaryButton>
    <SecondaryButton @click="router.push('/elder/add/manual')">改用手動輸入</SecondaryButton>

    <input
      ref="cameraInput"
      class="sr-only"
      type="file"
      accept="image/*"
      capture="environment"
      tabindex="-1"
      aria-hidden="true"
      @change="onFileChange"
    />
    <input
      ref="albumInput"
      class="sr-only"
      type="file"
      accept="image/*"
      tabindex="-1"
      aria-hidden="true"
      @change="onFileChange"
    />
  </PageLayout>
</template>

<style scoped>
.photo-area {
  flex: 1 1 auto;
  width: 100%;
  min-height: 300px;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  gap: 12px;
  padding: 24px 16px;
  border-radius: 16px;
  border: 3px dashed var(--color-primary-300);
  background: var(--color-primary-50);
  text-align: center;
}
.photo-area .title {
  color: var(--color-primary-700);
}
.photo-area .hint {
  color: var(--text-second);
}
.preview {
  width: 100%;
  max-height: 360px;
  object-fit: contain;
  border-radius: 12px;
  background: var(--background-color);
}
.reading {
  padding: 12px 16px;
  border-radius: 8px;
  background: var(--color-primary-50);
  border: 1px solid var(--color-primary-300);
  color: var(--color-primary-700);
}
.failed {
  display: flex;
  flex-direction: column;
  gap: 4px;
  padding: 12px 16px;
  border-radius: 8px;
  border: 2px solid var(--alarm-red-500);
  background: var(--background-color);
  color: var(--alarm-red-500);
}
.failed .title {
  font-size: var(--font-title-size);
}
.failed .lines {
  color: var(--text-second);
  overflow-wrap: anywhere;
}
</style>
