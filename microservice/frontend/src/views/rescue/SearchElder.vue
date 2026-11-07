<script setup lang="ts">
/** RE-PG-02 救護人員：查詢長者（身分證字號 10 碼；查無資料時顯示錯誤狀態 R02b） */
import { ref, watch } from 'vue'
import { useRouter } from 'vue-router'
import PageLayout from '@/components/PageLayout.vue'
import TextField from '@/components/inputs/TextField.vue'
import InfoNotice from '@/components/alerts/InfoNotice.vue'
import PrimaryButton from '@/components/buttons/PrimaryButton.vue'
import { rescueSearch } from '@/store'

const router = useRouter()
const idNumber = ref('')
const error = ref('')

watch(idNumber, (v) => {
  const upper = v.toUpperCase().replace(/[^A-Z0-9]/g, '').slice(0, 10)
  if (upper !== v) idNumber.value = upper
  error.value = ''
})

function search() {
  if (!/^[A-Z][0-9A-Z]\d{8}$/.test(idNumber.value) || !rescueSearch(idNumber.value)) {
    error.value = '查無此身分證字號的緊急醫療卡，請確認後重新輸入。'
    return
  }
  router.push('/rescue/card')
}
</script>

<template>
  <PageLayout title="查詢緊急醫療卡" fallback="/rescue">
    <h2 class="page-heading">輸入長者的身分證字號</h2>
    <TextField
      v-model="idNumber"
      label="身分證字號"
      required
      placeholder="例如：A123456789"
      :maxlength="10"
      help-text="共 10 碼"
      :error-text="error"
    />
    <InfoNotice>每次查詢都會記錄，並通知長者的家屬。</InfoNotice>
    <div class="flex-spacer" />
    <PrimaryButton @click="search">查詢</PrimaryButton>
  </PageLayout>
</template>
