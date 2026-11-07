<script setup lang="ts">
/**
 * FM-PG-01 家屬：登入
 * 使用台北通帳號（App 內透過 userinfo 取得帳號；瀏覽器使用模擬帳號）
 * 登入後：尚未綁定長輩 → FM-PG-02；已綁定 → FM-PG-03
 */
import { ref } from 'vue'
import { useRouter } from 'vue-router'
import PageLayout from '@/components/PageLayout.vue'
import PrimaryButton from '@/components/buttons/PrimaryButton.vue'
import { getUserInfo } from '@/composables/flutterBridge'
import { familyLogin, state } from '@/store'

const router = useRouter()
const loading = ref(false)

async function login() {
  loading.value = true
  const account = await getUserInfo()
  familyLogin(account?.realName)
  loading.value = false
  router.replace(state.familyUser.bound ? '/family/home' : '/family/bind')
}
</script>

<template>
  <PageLayout hide-nav centered :padding-top="80">
    <!-- illustration_icon_gov（裝飾圖） -->
    <svg width="160" height="160" viewBox="0 0 160 160" aria-hidden="true" focusable="false">
      <circle cx="80" cy="80" r="72" fill="#EDF8FA" />
      <path d="M40 70h80L80 42z" fill="#5AB4C5" />
      <rect x="48" y="72" width="10" height="38" fill="#356C77" />
      <rect x="75" y="72" width="10" height="38" fill="#356C77" />
      <rect x="102" y="72" width="10" height="38" fill="#356C77" />
      <rect x="40" y="110" width="80" height="10" rx="2" fill="#5AB4C5" />
    </svg>
    <h1 class="title font-h1-semibold">藥報平安</h1>
    <p class="page-desc">家屬版：隨時知道長輩今天要吃什麼藥</p>
    <div class="flex-spacer" />
    <PrimaryButton :disabled="loading" @click="login">使用台北通登入</PrimaryButton>
  </PageLayout>
</template>

<style scoped>
.title {
  color: var(--text-primary);
}
</style>
