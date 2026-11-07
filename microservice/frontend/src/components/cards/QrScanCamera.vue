<script setup lang="ts">
/**
 * EL-CRD-07 相機掃描區：偵測到 QR Code 自動辨識
 * - 瀏覽器支援 BarcodeDetector 時，自行從相機畫面辨識
 * - App 內則由 App 內建 qr_code_scan 掃描（見 EL-PG-06）
 * - 無法掃描時通知外層顯示「掃描失敗」：瀏覽器不支援、或一段時間內都沒偵測到
 */
import { onBeforeUnmount, ref, watch } from 'vue'
import CameraArea from './CameraArea.vue'

export type ScanFailReason = 'unsupported' | 'timeout'

const emit = defineEmits<{ detected: [raw: string]; failed: [reason: ScanFailReason] }>()

/** 幾秒內都沒偵測到二維碼就提示掃描失敗（仍會繼續掃描） */
const TIMEOUT_MS = 20_000

const area = ref<InstanceType<typeof CameraArea> | null>(null)
let timer = 0
let timeoutTimer = 0
/** 上一次送出的內容：同一張 QR Code 持續對著鏡頭時不重複送出（不是藥單時可繼續掃下一張） */
let lastRaw = ''

function armTimeout() {
  window.clearTimeout(timeoutTimer)
  timeoutTimer = window.setTimeout(() => emit('failed', 'timeout'), TIMEOUT_MS)
}

function startDetect() {
  const Detector = window.BarcodeDetector
  const video = area.value?.video
  if (!video) return
  if (!Detector) {
    emit('failed', 'unsupported')
    return
  }
  const detector = new Detector({ formats: ['qr_code'] })
  window.clearInterval(timer)
  armTimeout()
  timer = window.setInterval(async () => {
    if (video.readyState < 2) return
    try {
      const codes = await detector.detect(video)
      const raw = codes[0]?.rawValue
      if (raw && raw !== lastRaw) {
        lastRaw = raw
        armTimeout()
        emit('detected', raw)
      }
    } catch {
      /* 偵測失敗時下一輪再試 */
    }
  }, 500)
}

function stopDetect() {
  window.clearInterval(timer)
  window.clearTimeout(timeoutTimer)
}

watch(
  () => area.value?.ready,
  (ready) => {
    if (ready) startDetect()
    else stopDetect()
  },
)

onBeforeUnmount(stopDetect)
</script>

<template>
  <CameraArea ref="area" hint="把 QR Code 對準框框" :frame-width="300" :frame-height="300" />
</template>
