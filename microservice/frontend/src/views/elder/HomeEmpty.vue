<script setup lang="ts">
/**
 * EL-PG-02 長者：首頁（無藥）
 * 回診預約與用藥互相獨立：沒有藥單時，有預約仍顯示「下次回診」
 */
import { computed } from 'vue'
import { useRouter } from 'vue-router'
import PageLayout from '@/components/PageLayout.vue'
import EmptyStateCard from '@/components/cards/EmptyStateCard.vue'
import NextVisitCard from '@/components/cards/NextVisitCard.vue'
import PrimaryButton from '@/components/buttons/PrimaryButton.vue'
import FeatureEntry from '@/components/cards/FeatureEntry.vue'
import StaffEntryButton from '@/components/buttons/StaffEntryButton.vue'
import GreetingBlock from './GreetingBlock.vue'
import { upcomingAppointments } from '@/store'
import type { IconName } from '@/components/AppIcon.vue'

const props = defineProps<{ now: Date }>()
const router = useRouter()

const appointments = computed(() => upcomingAppointments(props.now))

const entries: { icon: IconName; title: string; subtitle: string; to: string }[] = [
  { icon: 'calendar', title: '回診預約', subtitle: '北市聯醫各院區', to: '/elder/booking' },
  { icon: 'medical-card', title: '緊急醫療卡', subtitle: '緊急時讓救護人員看得到', to: '/elder/card' },
  { icon: 'invite', title: '邀請家屬', subtitle: '家屬也會收到用藥提醒', to: '/elder/invite' },
]
</script>

<template>
  <PageLayout>
    <GreetingBlock :now="now" />
    <EmptyStateCard />
    <PrimaryButton @click="router.push('/elder/add')">新增藥單</PrimaryButton>
    <NextVisitCard
      v-for="(a, i) in appointments"
      :key="`${a.date}-${a.time}-${a.doctor}`"
      :appointment="a"
      :later="i > 0"
    />
    <h2 class="section-label">功能</h2>
    <FeatureEntry
      v-for="e in entries"
      :key="e.title"
      :icon="e.icon"
      :title="e.title"
      :subtitle="e.subtitle"
      @click="router.push(e.to)"
    />

    <StaffEntryButton />
  </PageLayout>
</template>
