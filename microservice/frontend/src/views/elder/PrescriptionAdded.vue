<script setup lang="ts">
/**
 * EL-PG-19 長者：藥單加入完成（Figma E07，node 10:2317）
 * - 提示在實體藥袋寫上字母，對應手機上的編號
 * - 列出四個時段各吃哪幾號；已吃完的藥單不會提醒，改顯示提示
 * - 「查看我的藥單」→ EL-PG-18（E08）；返回鍵回首頁（不回到已送出的確認頁）
 */
import { computed, onMounted } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import PageLayout from '@/components/PageLayout.vue'
import WarningNotice from '@/components/alerts/WarningNotice.vue'
import InfoNotice from '@/components/alerts/InfoNotice.vue'
import InfoList from '@/components/cards/InfoList.vue'
import PrimaryButton from '@/components/buttons/PrimaryButton.vue'
import { SLOTS } from '@/data/constants'
import { isFinished, state } from '@/store'
import { isLongExpired } from '@/utils/supply'

const route = useRoute()
const router = useRouter()
const now = new Date()

const rx = computed(() => state.prescriptions.find((p) => p.id === route.params.id))
const codes = computed(() => rx.value?.medicines.map((m) => m.code).join('、') ?? '')
const finished = computed(() => !!rx.value && isFinished(rx.value, now))
/** 字母徽章色系比照 RxBadge：A、C、E… 藍綠底白字；B、D、F… 黃底深字 */
const tone = computed(() => ((rx.value?.code.charCodeAt(0) ?? 65) - 65) % 2 === 0 ? 'primary' : 'secondary')

/** 四個時段各吃哪幾號；沒有藥的時段顯示「—」 */
const rows = computed(() =>
  SLOTS.map((slot) => ({
    label: `${slot.name} ${slot.time}`,
    value: rx.value?.medicines.filter((m) => m.slots.includes(slot.key)).map((m) => m.code).join('、') || '—',
  })),
)

onMounted(() => {
  // 直接開啟網址或找不到藥單時，改到我的藥單
  if (!rx.value) router.replace('/elder/prescriptions')
})
</script>

<template>
  <PageLayout title="加入完成" fallback="/elder" :on-back="() => router.replace('/elder')">
    <template v-if="rx">
      <div class="done">
        <span class="letter font-h1-semibold" :class="tone" aria-hidden="true">{{ rx.code }}</span>
        <h2 class="font-h2-semibold">藥單 {{ rx.code }} 加好了</h2>
      </div>
      <WarningNotice>
        請用筆在這個藥袋上寫一個大大的「{{ rx.code }}」。手機上的 {{ codes }}，就是這個藥袋裡的藥。
      </WarningNotice>

      <template v-if="!finished">
        <h3 class="font-h3-semibold">已經幫您排好吃藥時間</h3>
        <InfoList :rows="rows" label="吃藥時間" />
        <InfoNotice>時間到會通知您和家屬。</InfoNotice>
      </template>
      <WarningNotice v-else>
        {{
          isLongExpired(rx, now)
            ? '這張藥單已經吃完超過 3 個月，不會提醒吃藥，也不會顯示在「我的藥單」。'
            : '這張藥單已經吃完了，不會提醒吃藥。可以在「我的藥單」的「已吃完」查看。'
        }}
      </WarningNotice>

      <div class="flex-spacer" />
      <PrimaryButton @click="router.replace('/elder/prescriptions')">查看我的藥單</PrimaryButton>
    </template>
  </PageLayout>
</template>

<style scoped>
.done {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 12px;
  padding-top: 8px;
  text-align: center;
  color: var(--text-primary);
}
.letter {
  width: 96px;
  height: 96px;
  border-radius: 48px;
  display: inline-flex;
  align-items: center;
  justify-content: center;
}
.primary {
  background: var(--color-primary-700);
  color: var(--color-white);
}
.secondary {
  background: var(--color-secondary-500);
  color: var(--text-primary);
}
h3 {
  color: var(--text-primary);
}
</style>
