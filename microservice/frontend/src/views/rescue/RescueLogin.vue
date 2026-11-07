<script setup lang="ts">
/** RE-PG-01 救護人員：登入（所屬單位、人員編號、密碼皆必填；密碼遮蔽） */
import { computed, ref } from 'vue'
import { useRouter } from 'vue-router'
import PageLayout from '@/components/PageLayout.vue'
import WarningNotice from '@/components/alerts/WarningNotice.vue'
import SelectField from '@/components/inputs/SelectField.vue'
import TextField from '@/components/inputs/TextField.vue'
import PrimaryButton from '@/components/buttons/PrimaryButton.vue'
import SelectSheet from '@/components/overlays/SelectSheet.vue'
import { RESCUE_UNITS } from '@/data/mock'
import { rescueLogin, state } from '@/store'

const router = useRouter()

const unit = ref(state.rescue?.unit ?? RESCUE_UNITS[0].value)
const staffId = ref(state.rescue?.staffId ?? '')
const password = ref('')
const sheetOpen = ref(false)
const tried = ref(false)
const loginError = ref('')
const loggingIn = ref(false)

const REQUIRED = '此欄必填'
const staffError = computed(() => (tried.value && !staffId.value.trim() ? REQUIRED : ''))
const passwordError = computed(() => (tried.value && !password.value ? REQUIRED : ''))

async function login() {
  tried.value = true
  loginError.value = ''
  if (!unit.value || !staffId.value.trim() || !password.value || loggingIn.value) return
  loggingIn.value = true
  try {
    await rescueLogin(unit.value, staffId.value.trim().toUpperCase(), password.value)
    router.push('/rescue/search')
  } catch (e) {
    // 單位、編號、密碼錯誤：「單位、人員編號或密碼錯誤」；已離職：「無權限」
    loginError.value = e instanceof Error ? e.message : '登入失敗，請再試一次'
  } finally {
    loggingIn.value = false
  }
}
</script>

<template>
  <PageLayout title="救護人員專用">
    <h2 class="page-heading">救護人員登入</h2>
    <WarningNotice>僅限執勤中的救護人員使用，所有查詢都會記錄。</WarningNotice>
    <SelectField label="所屬單位" :value="unit" @open="sheetOpen = true" />
    <TextField
      v-model="staffId"
      label="人員編號"
      required
      placeholder="例如：A12345"
      autocomplete="username"
      :error-text="staffError"
    />
    <TextField
      v-model="password"
      label="密碼"
      required
      type="password"
      autocomplete="current-password"
      :error-text="passwordError"
    />
    <WarningNotice v-if="loginError" role="alert">{{ loginError }}</WarningNotice>
    <div class="flex-spacer" />
    <PrimaryButton :disabled="loggingIn" @click="login">{{ loggingIn ? '登入中…' : '登入' }}</PrimaryButton>

    <SelectSheet
      :open="sheetOpen"
      title="選擇所屬單位"
      :options="RESCUE_UNITS"
      :selected="unit"
      show-check
      @close="sheetOpen = false"
      @select="(v) => { unit = v; sheetOpen = false }"
    />
  </PageLayout>
</template>
