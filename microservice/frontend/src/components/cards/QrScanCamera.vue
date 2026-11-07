<script setup lang="ts">
/**
 * EL-CRD-07 相機掃描區：偵測到 QR Code 自動辨識
 * - 瀏覽器支援 BarcodeDetector 時，自行從相機畫面辨識
 * - App 內則由 App 內建 qr_code_scan 掃描（見 EL-PG-06）
 */
import { onBeforeUnmount, ref, watch } from 'vue'
import CameraArea from './CameraArea.vue'

const emit = defineEmits<{ detected: [raw: string] }>()

const area = ref<InstanceType<typeof CameraArea> | null>(null)
let timer = 0
let done = false

function startDetect() {
  const Detector = window.BarcodeDetector
  const video = area.value?.video
  if (!Detector || !video) return
  const detector = new Detector({ formats: ['qr_code'] })
  window.clearInterval(timer)
  timer = window.setInterval(async () => {
    if (done || video.readyState < 2) return
    try {
      const codes = await detector.detect(video)
      if (codes.length && !done) {
        done = true
        window.clearInterval(timer)
        emit('detected', codes[0].rawValue)
      }
    } catch {
      /* 偵測失敗時下一輪再試 */
    }
  }, 500)
}

watch(
  () => area.value?.ready,
  (ready) => {
    if (ready) startDetect()
    else window.clearInterval(timer)
  },
)

onBeforeUnmount(() => window.clearInterval(timer))
</script>

<template>
  <CameraArea ref="area" hint="把 QR Code 對準框框" :frame-width="300" :frame-height="300" />
</template>
