<script setup lang="ts">
/**
 * EL-PG-06 長者：掃描藥袋 QR Code
 * - App 內：開啟 App 內建 qr_code_scan，掃描成功自動跳轉
 * - 瀏覽器：相機畫面＋BarcodeDetector 自動辨識
 */
import { onMounted } from 'vue'
import { useRouter } from 'vue-router'
import PageLayout from '@/components/PageLayout.vue'
import QrScanCamera from '@/components/cards/QrScanCamera.vue'
import SecondaryButton from '@/components/buttons/SecondaryButton.vue'
import { isInApp, scanQrCode } from '@/composables/flutterBridge'
import { startDraftFromRecognition } from '@/store'
import { parsePrescriptionQr } from '@/utils/qr'

const router = useRouter()

function onDetected(raw: string) {
  startDraftFromRecognition(parsePrescriptionQr(raw))
  router.replace('/elder/add/review')
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
    <SecondaryButton @click="router.replace('/elder/add/photo')">改用拍照</SecondaryButton>
  </PageLayout>
</template>
