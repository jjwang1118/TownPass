<script setup lang="ts">
/**
 * 頁面骨架：導覽列＋可垂直捲動內容區
 * 內容區：padding 上 16、下 24、左右 16；gap 16；垂直排列
 */
import { useRouter, type RouteLocationRaw } from 'vue-router'
import AppHeader from '@/components/nav/AppHeader.vue'
import BackHeader from '@/components/nav/BackHeader.vue'

const props = withDefaults(
  defineProps<{
    /** 有值時使用 CM-NAV-02（返回＋標題），否則使用 CM-NAV-01 */
    title?: string
    /** 沒有上一頁歷史時，返回鍵導向此處 */
    fallback?: RouteLocationRaw
    /** 自訂返回行為（例如鎖定返回） */
    onBack?: () => void
    centered?: boolean
    paddingTop?: number
    /** 不顯示導覽列（例：FM-PG-01 登入頁） */
    hideNav?: boolean
  }>(),
  { centered: false, paddingTop: 16, hideNav: false },
)

const router = useRouter()

function back() {
  if (props.onBack) {
    props.onBack()
    return
  }
  if (window.history.state?.back) router.back()
  else if (props.fallback) router.replace(props.fallback)
}
</script>

<template>
  <div class="page">
    <template v-if="!hideNav">
      <BackHeader v-if="title" :title="title" @back="back" />
      <AppHeader v-else />
    </template>
    <main class="content" :class="{ centered }" :style="{ paddingTop: `${paddingTop}px` }">
      <slot />
    </main>
  </div>
</template>

<style scoped>
.page {
  display: flex;
  flex-direction: column;
  min-height: 100vh;
  min-height: 100dvh;
}
.content {
  flex: 1 1 auto;
  display: flex;
  flex-direction: column;
  gap: var(--page-gap);
  padding: var(--page-padding-top) var(--page-padding-x) calc(var(--page-padding-bottom) + env(safe-area-inset-bottom));
}
.content.centered {
  align-items: center;
  text-align: center;
}
</style>
