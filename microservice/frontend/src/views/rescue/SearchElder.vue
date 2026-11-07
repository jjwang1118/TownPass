<script setup lang="ts">
/**
 * RE-PG-02 救護人員：查詢長者的緊急醫療卡（查無資料時顯示錯誤狀態 R02b）
 * 不使用身分證字號：輸入長者敬老卡背面貼紙或手機桌布上的卡號（TPE-XXXX-XXXX），
 * 或在台北通 App 內掃卡片上的 QR Code。
 */
import { ref, watch } from 'vue'
import { useRouter } from 'vue-router'
import PageLayout from '@/components/PageLayout.vue'
import TextField from '@/components/inputs/TextField.vue'
import InfoNotice from '@/components/alerts/InfoNotice.vue'
import PrimaryButton from '@/components/buttons/PrimaryButton.vue'
import SecondaryButton from '@/components/buttons/SecondaryButton.vue'
import { rescueSearch } from '@/store'
import { isInApp, scanQrCode } from '@/composables/flutterBridge'

const router = useRouter()
const code = ref('')
const error = ref('')
const searching = ref(false)
const inApp = isInApp()

const NOT_FOUND = '查無此卡號的緊急醫療卡，請確認後重新輸入。'

watch(code, (v) => {
  // 只保留英數與連字號，自動轉大寫
  const upper = v.toUpperCase().replace(/[^A-Z0-9-]/g, '').slice(0, 13)
  if (upper !== v) code.value = upper
  error.value = ''
})

async function run(input: { code?: string; qr?: string }) {
  if (searching.value) return
  searching.value = true
  try {
    if (await rescueSearch(input)) router.push('/rescue/card')
    else error.value = NOT_FOUND
  } catch (e) {
    error.value = e instanceof Error ? e.message : '查詢失敗，請再試一次。'
    if (e instanceof Error && 'status' in e && (e as { status: number }).status === 401) router.replace('/rescue')
  } finally {
    searching.value = false
  }
}

function search() {
  if (code.value.replace(/-/g, '').length < 8) {
    error.value = NOT_FOUND
    return
  }
  run({ code: code.value })
}

async function scan() {
  const raw = await scanQrCode()
  if (raw) run({ qr: raw })
}
</script>

<template>
  <PageLayout title="查詢緊急醫療卡" fallback="/rescue">
    <h2 class="page-heading">輸入緊急醫療卡卡號</h2>
    <TextField
      v-model="code"
      label="卡號"
      required
      placeholder="例如：TPE-7K3Q-9X2M"
      :maxlength="13"
      help-text="在長者敬老卡背面的貼紙或手機桌布上"
      :error-text="error"
    />
    <SecondaryButton v-if="inApp" @click="scan">掃描卡片上的 QR Code</SecondaryButton>
    <InfoNotice>每次查詢都會記錄，並通知長者的家屬。</InfoNotice>
    <div class="flex-spacer" />
    <PrimaryButton :disabled="searching" @click="search">{{ searching ? '查詢中…' : '查詢' }}</PrimaryButton>
  </PageLayout>
</template>
