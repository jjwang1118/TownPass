<script setup lang="ts">
/**
 * 輸入邀請碼綁定長輩（FM-PG-02，含錯誤狀態 F02b）；FM-PG-02 與 EL-PG-17「綁定長輩」分頁共用
 * - 家屬（預設）：用家屬帳號綁定，成功 → 家屬首頁 FM-PG-03
 * - asElder：長輩用自己的帳號綁定另一位長輩，成功後留在原頁並通知（bound）；輸入自己的邀請碼時提示
 */
import { ref, watch } from 'vue'
import { useRouter } from 'vue-router'
import TextField from '@/components/inputs/TextField.vue'
import PrimaryButton from '@/components/buttons/PrimaryButton.vue'
import { bindAsElder, bindWithInviteCode } from '@/store'

const props = defineProps<{ asElder?: boolean }>()
const emit = defineEmits<{ bound: [] }>()

const router = useRouter()
const code = ref('')
const error = ref('')

const ERROR_TEXT = '邀請碼不正確或已過期，請長輩按「換一組數字」再試一次。'
const SELF_TEXT = '這是您自己的邀請碼，請輸入對方的邀請碼。'

watch(code, (v) => {
  // 只保留數字
  const digits = v.replace(/\D/g, '').slice(0, 6)
  if (digits !== v) code.value = digits
  error.value = ''
})

const binding = ref(false)

async function bind(): Promise<void> {
  if (props.asElder) {
    const result = await bindAsElder(code.value)
    if (result === 'ok') {
      code.value = ''
      emit('bound')
    } else error.value = result === 'self' ? SELF_TEXT : ERROR_TEXT
    return
  }
  if (await bindWithInviteCode(code.value)) router.replace('/family/home')
  else error.value = ERROR_TEXT
}

async function submit() {
  if (!/^\d{6}$/.test(code.value)) {
    error.value = ERROR_TEXT
    return
  }
  if (binding.value) return
  binding.value = true
  try {
    await bind()
  } catch {
    /* 連線錯誤由畫面上方的提示顯示 */
  } finally {
    binding.value = false
  }
}
</script>

<template>
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
  <!-- 家屬頁按鈕固定在底部（FM-PG-02）；長輩分頁下方還有「我關心的長輩」清單 -->
  <div v-if="!asElder" class="flex-spacer" />
  <PrimaryButton :disabled="binding" @click="submit">確認綁定</PrimaryButton>
  <slot />
</template>
