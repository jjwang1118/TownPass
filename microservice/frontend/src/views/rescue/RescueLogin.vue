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

const REQUIRED = '此欄必填'
const staffError = computed(() => (tried.value && !staffId.value.trim() ? REQUIRED : ''))
const passwordError = computed(() => (tried.value && !password.value ? REQUIRED : ''))

function login() {
  tried.value = true
  if (!unit.value || !staffId.value.trim() || !password.value) return
  rescueLogin(unit.value, staffId.value.trim().toUpperCase())
  router.push('/rescue/search')
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
    <div class="flex-spacer" />
    <PrimaryButton @click="login">登入</PrimaryButton>

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
