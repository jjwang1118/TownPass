<script setup lang="ts">
/** FM-PG-02 家屬：輸入邀請碼（含錯誤狀態 F02b） */
import { ref, watch } from 'vue'
import { useRouter } from 'vue-router'
import PageLayout from '@/components/PageLayout.vue'
import TextField from '@/components/inputs/TextField.vue'
import PrimaryButton from '@/components/buttons/PrimaryButton.vue'
import { bindWithInviteCode } from '@/store'

const router = useRouter()
const code = ref('')
const error = ref('')

const ERROR_TEXT = '邀請碼不正確或已過期，請長輩按「換一組數字」再試一次。'

watch(code, (v) => {
  // 只保留數字
  const digits = v.replace(/\D/g, '').slice(0, 6)
  if (digits !== v) code.value = digits
  error.value = ''
})

const binding = ref(false)

async function submit() {
  if (!/^\d{6}$/.test(code.value)) {
    error.value = ERROR_TEXT
    return
  }
  if (binding.value) return
  binding.value = true
  try {
    if (await bindWithInviteCode(code.value)) router.replace('/family/home')
    else error.value = ERROR_TEXT
  } catch {
    /* 連線錯誤由畫面上方的提示顯示 */
  } finally {
    binding.value = false
  }
}
</script>

<template>
  <PageLayout title="綁定長輩" fallback="/family">
    <h2 class="page-heading">輸入長輩的邀請碼</h2>
    <p class="page-desc">請長輩打開「呷藥囉」→「邀請家屬」，把畫面上的 6 位數字告訴您。</p>
    <TextField
      v-model="code"
      label="邀請碼"
      required
      placeholder="6 位數字"
      inputmode="numeric"
      autocomplete="one-time-code"
      :maxlength="6"
      help-text="共 6 位數字"
      :error-text="error"
    />
    <div class="flex-spacer" />
    <PrimaryButton @click="submit">確認綁定</PrimaryButton>
  </PageLayout>
</template>
