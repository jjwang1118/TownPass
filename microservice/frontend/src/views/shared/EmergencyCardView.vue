<script setup lang="ts">
/**
 * 緊急醫療卡共用版面：EL-PG-15（長者，可編輯）／FM-PG-05（家屬，只能查看）
 * 第一次使用時醫療卡為空：顯示「還沒有填寫」提示；填了才顯示醫療卡內容（只列有填的欄位）
 */
import { computed } from 'vue'
import PageLayout from '@/components/PageLayout.vue'
import InfoNotice from '@/components/alerts/InfoNotice.vue'
import EmergencyCardBody from '@/components/cards/EmergencyCardBody.vue'
import InfoList from '@/components/cards/InfoList.vue'
import { activeMedicines, state } from '@/store'
import { formatDateTime } from '@/utils/date'
import { isCardEmpty } from '@/utils/card'

const props = defineProps<{ viewer: 'elder' | 'family'; notices: string[]; fallback: string }>()

const medicines = computed(() => activeMedicines(new Date()))
const empty = computed(() => isCardEmpty(state.card) && medicines.value.length === 0)
const emptyTitle = computed(() => (props.viewer === 'family' ? '長輩還沒有填寫緊急醫療卡' : '還沒有填寫緊急醫療卡'))
const emptyDesc = computed(() =>
  props.viewer === 'family'
    ? '長輩填寫後，您就可以在這裡查看。'
    : '填寫後，緊急時救護人員和家屬就能看到您的病史、過敏和緊急聯絡人。',
)

/** 查看紀錄依時間新到舊 */
const logs = computed(() =>
  [...state.viewLogs]
    .sort((a, b) => new Date(b.time).getTime() - new Date(a.time).getTime())
    .map((l) => ({ label: formatDateTime(l.time), value: l.viewer })),
)
</script>

<template>
  <PageLayout title="緊急醫療卡" :fallback="fallback">
    <InfoNotice v-for="n in notices" :key="n">{{ n }}</InfoNotice>

    <section v-if="empty" class="empty-card" aria-labelledby="empty-card-title">
      <h2 id="empty-card-title" class="font-h2-semibold">{{ emptyTitle }}</h2>
      <p class="page-desc">{{ emptyDesc }}</p>
    </section>
    <template v-else>
      <EmergencyCardBody :card="state.card" :medicines="medicines" :viewer="viewer" />
      <h2 class="section-label">誰看過我的醫療卡</h2>
      <InfoList v-if="logs.length" :rows="logs" label="查看紀錄" />
      <p v-else class="page-desc">還沒有人查看過。</p>
    </template>
    <slot />
  </PageLayout>
</template>

<style scoped>
.empty-card {
  display: flex;
  flex-direction: column;
  gap: 8px;
  padding: 24px 16px;
  border-radius: 12px;
  border: 2px dashed var(--alarm-red-500);
  text-align: center;
  color: var(--text-primary);
}
</style>
