<script setup lang="ts">
/**
 * EL-PG-16 長者：編輯緊急醫療卡
 * - 必填：姓名、出生年月日、聯絡人姓名、關係、電話、藥物過敏、食物過敏（沒有則填「無」）
 * - 緊急聯絡人只有一位；不收集常去醫院與病歷號（UI E14）
 * - 目前用藥自動帶入，不可編輯
 * - 必須勾選同意書才能儲存
 */
import { computed, reactive, ref } from 'vue'
import { useRouter } from 'vue-router'
import PageLayout from '@/components/PageLayout.vue'
import InfoNotice from '@/components/alerts/InfoNotice.vue'
import WarningNotice from '@/components/alerts/WarningNotice.vue'
import TextField from '@/components/inputs/TextField.vue'
import OptionChips from '@/components/segments/OptionChips.vue'
import CheckRow from '@/components/inputs/CheckRow.vue'
import PrimaryButton from '@/components/buttons/PrimaryButton.vue'
import { BLOOD_OPTIONS, CHRONIC_OPTIONS, GENDER_OPTIONS, LANGUAGE_OPTIONS, SPECIAL_OPTIONS } from '@/data/constants'
import { activeMedicines, saveCard, state } from '@/store'
import type { EmergencyCard } from '@/types'

const router = useRouter()

// 第一次填寫時醫療卡為空，所有欄位從空白開始
const form = reactive<EmergencyCard>(JSON.parse(JSON.stringify(state.card)) as EmergencyCard)
const tried = ref(false)
const saving = ref(false)
const saveError = ref('')

// EL-SEG-02 以字串綁定
const gender = computed({ get: () => form.gender, set: (v) => (form.gender = v as EmergencyCard['gender']) })
const blood = computed({ get: () => form.bloodType, set: (v) => (form.bloodType = v as EmergencyCard['bloodType']) })
const language = computed({ get: () => form.language, set: (v) => (form.language = v as EmergencyCard['language']) })

const medicinesText = computed(() =>
  activeMedicines(new Date())
    .map((m) => `${m.code} ${m.name.split(' ')[0]}`)
    .join('、') || '目前沒有藥單',
)

const REQUIRED_MSG = '此欄必填，沒有請填「無」'
const err = (v: string) => (tried.value && !v.trim() ? REQUIRED_MSG : '')
const birthdayError = computed(() => {
  if (!tried.value) return ''
  if (!form.birthday.trim()) return REQUIRED_MSG
  return /^\d{4}\/\d{1,2}\/\d{1,2}$/.test(form.birthday.trim()) ? '' : '請依照 1948/05/12 的格式填寫'
})

const requiredValues = computed(() => [
  form.name,
  form.contact1.name,
  form.contact1.relation,
  form.contact1.phone,
  form.drugAllergy,
  form.foodAllergy,
])

async function save() {
  tried.value = true
  if (requiredValues.value.some((v) => !v.trim()) || birthdayError.value) {
    window.requestAnimationFrame(() => document.querySelector<HTMLElement>('[aria-invalid="true"]')?.focus())
    return
  }
  if (saving.value) return
  saving.value = true
  saveError.value = ''
  try {
    await saveCard({ ...form, birthday: form.birthday.trim(), consent: true })
  } catch (e) {
    saveError.value = e instanceof Error ? e.message : '儲存失敗，請再試一次'
    return
  } finally {
    saving.value = false
  }
  if (window.history.state?.back) router.back()
  else router.replace('/elder/card')
}
</script>

<template>
  <PageLayout title="編輯緊急醫療卡" fallback="/elder/card">
    <InfoNotice>可以請家人幫忙填寫。目前用藥會從藥單自動帶入。</InfoNotice>

    <h2 class="group-title">基本資料</h2>
    <TextField v-model="form.name" label="姓名" required autocomplete="name" :error-text="err(form.name)" />
    <TextField
      v-model="form.birthday"
      label="出生年月日"
      required
      placeholder="例如：1948/05/12"
      inputmode="numeric"
      :error-text="birthdayError"
    />
    <h3 class="field-label">性別</h3>
    <OptionChips v-model="gender" :options="GENDER_OPTIONS" label="性別" />
    <h3 class="field-label">血型</h3>
    <OptionChips v-model="blood" :options="BLOOD_OPTIONS" label="血型" />

    <h2 class="group-title">緊急聯絡人</h2>
    <TextField v-model="form.contact1.name" label="聯絡人姓名" required :error-text="err(form.contact1.name)" />
    <TextField v-model="form.contact1.relation" label="關係" required placeholder="例如：女兒" :error-text="err(form.contact1.relation)" />
    <TextField
      v-model="form.contact1.phone"
      label="電話"
      required
      type="tel"
      inputmode="tel"
      autocomplete="tel"
      :error-text="err(form.contact1.phone)"
    />

    <h2 class="group-title">身體狀況</h2>
    <h3 class="field-label">慢性病（可以選很多個）</h3>
    <OptionChips v-model="form.chronic" :options="CHRONIC_OPTIONS" multiple label="慢性病" />
    <TextField
      v-model="form.drugAllergy"
      label="藥物過敏"
      required
      help-text="沒有請填「無」"
      :error-text="err(form.drugAllergy)"
    />
    <TextField v-model="form.foodAllergy" label="食物過敏" required :error-text="err(form.foodAllergy)" />
    <div class="readonly">
      <h3 class="field-label">目前用藥（從藥單自動帶入）</h3>
      <p class="font-h3-regular text-primary">{{ medicinesText }}</p>
    </div>
    <h3 class="field-label">特殊狀況</h3>
    <OptionChips v-model="form.special" :options="SPECIAL_OPTIONS" multiple label="特殊狀況" />

    <h2 class="group-title">溝通</h2>
    <h3 class="field-label">慣用語言</h3>
    <OptionChips v-model="language" :options="LANGUAGE_OPTIONS" label="慣用語言" />

    <h2 class="group-title">同意書</h2>
    <p class="page-desc">緊急醫療卡只會在需要時，給綁定的家屬和經過驗證的救護人員查看，每次查看都會留下紀錄。</p>
    <CheckRow v-model="form.consent">我同意救護人員與綁定家屬在需要時查看這張醫療卡</CheckRow>

    <WarningNotice v-if="saveError" role="alert">{{ saveError }}</WarningNotice>
    <PrimaryButton :disabled="!form.consent || saving" @click="save">{{ saving ? '儲存中…' : '儲存' }}</PrimaryButton>
  </PageLayout>
</template>

<style scoped>
.group-title {
  font-size: var(--font-title-size);
  line-height: 1.5rem;
  font-weight: 700;
  color: var(--text-primary);
  margin-top: 8px;
}
.field-label {
  font-size: var(--font-h3-size);
  line-height: var(--font-h3-line);
  font-weight: 700;
  color: var(--color-grey-950);
}
.readonly {
  display: flex;
  flex-direction: column;
  gap: 8px;
  padding: 12px 16px;
  border-radius: 10px;
  background: var(--color-grey-50);
}
</style>
