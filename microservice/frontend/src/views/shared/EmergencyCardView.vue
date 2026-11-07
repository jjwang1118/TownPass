<script setup lang="ts">
/** 緊急醫療卡共用版面：EL-PG-15（長者，可編輯）／FM-PG-05（家屬，只能查看） */
import { computed } from 'vue'
import PageLayout from '@/components/PageLayout.vue'
import InfoNotice from '@/components/alerts/InfoNotice.vue'
import EmergencyCardBody from '@/components/cards/EmergencyCardBody.vue'
import InfoList from '@/components/cards/InfoList.vue'
import { activeMedicines, state } from '@/store'
import { formatDateTime } from '@/utils/date'

defineProps<{ viewer: 'elder' | 'family'; notices: string[]; fallback: string }>()

const medicines = computed(() => activeMedicines(new Date()))
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
    <EmergencyCardBody :card="state.card" :medicines="medicines" :viewer="viewer" />
    <h2 class="section-label">誰看過我的醫療卡</h2>
    <InfoList v-if="logs.length" :rows="logs" label="查看紀錄" />
    <p v-else class="page-desc">還沒有人查看過。</p>
    <slot />
  </PageLayout>
</template>
