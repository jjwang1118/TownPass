<script setup lang="ts">
/**
 * FM-PG-03 家屬：首頁（只顯示時段總覽）
 * 註：切換長輩選單（ID 待定）與回診詳情（ID 待定）尚未建檔，目前不設點擊行為。
 */
import { computed } from 'vue'
import { useRouter } from 'vue-router'
import PageLayout from '@/components/PageLayout.vue'
import AppIcon from '@/components/AppIcon.vue'
import TimeSlotCard from '@/components/cards/TimeSlotCard.vue'
import NextVisitCard from '@/components/cards/NextVisitCard.vue'
import FeatureEntry from '@/components/cards/FeatureEntry.vue'
import { SLOTS } from '@/data/constants'
import { activeMedicines, state, upcomingAppointments } from '@/store'
import { useNow } from '@/composables/useNow'
import { phoneCall } from '@/composables/flutterBridge'
import { formatLongDate } from '@/utils/date'
import { medicinesInSlot, slotStatuses } from '@/utils/schedule'

const router = useRouter()
const now = useNow()

const elder = computed(() => state.elder)
const meds = computed(() => activeMedicines(now.value))
const statuses = computed(() => slotStatuses(now.value))
const appointments = computed(() => upcomingAppointments(now.value))
/** 「長輩的藥單」導向目前時段（沒有「現在」時段則為早上） */
const currentSlot = computed(() => SLOTS.find((s) => statuses.value[s.key] === 'now')?.key ?? 'morning')
</script>

<template>
  <!-- 長輩查看綁定的另一位長輩時，加返回鍵回到「綁定長輩」分頁 -->
  <PageLayout :title="state.familyUser.viaElder ? '關心的長輩' : undefined" fallback="/elder/invite?tab=bind">
    <div class="elder-row">
      <h2 class="page-heading">{{ elder.name }}今天的藥</h2>
      <AppIcon name="chevron-down" />
    </div>
    <p class="page-desc">{{ formatLongDate(now) }}｜綁定多位長輩時，點姓名切換</p>

    <div class="slots">
      <TimeSlotCard
        v-for="s in SLOTS"
        :key="s.key"
        :name="s.name"
        :time="s.time"
        :status="statuses[s.key]"
        :codes="medicinesInSlot(meds, s.key).map((m) => m.code)"
        @click="router.push(`/family/slot/${s.key}`)"
      />
    </div>

    <NextVisitCard
      v-for="(a, i) in appointments"
      :key="`${a.date}-${a.time}-${a.doctor}`"
      :appointment="a"
      viewer="family"
      :later="i > 0"
    />

    <FeatureEntry
      icon="phone"
      title="打電話給長輩"
      :subtitle="`${elder.name} ${elder.phone}`"
      @click="phoneCall(elder.phone)"
    />
    <FeatureEntry
      icon="my-rx"
      title="長輩的藥單"
      subtitle="看每一個編號是什麼藥"
      @click="router.push(`/family/slot/${currentSlot}`)"
    />
    <FeatureEntry
      icon="medical-card"
      title="長輩的緊急醫療卡"
      subtitle="只能查看，不能修改"
      @click="router.push('/family/card')"
    />
  </PageLayout>
</template>

<style scoped>
.elder-row {
  display: flex;
  align-items: center;
  gap: 8px;
  color: var(--text-second);
}
.slots {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(150px, 1fr));
  gap: 12px;
}
</style>
