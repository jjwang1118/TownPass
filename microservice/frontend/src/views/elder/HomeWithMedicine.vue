<script setup lang="ts">
/** EL-PG-01 長者：首頁（有藥） */
import { computed } from 'vue'
import { useRouter } from 'vue-router'
import PageLayout from '@/components/PageLayout.vue'
import MedicineCard from '@/components/cards/MedicineCard.vue'
import TimeSlotCard from '@/components/cards/TimeSlotCard.vue'
import NextVisitCard from '@/components/cards/NextVisitCard.vue'
import FeatureEntry from '@/components/cards/FeatureEntry.vue'
import LanguageSwitch from '@/components/segments/LanguageSwitch.vue'
import GreetingBlock from './GreetingBlock.vue'
import { SLOTS } from '@/data/constants'
import { activeMedicines, state, upcomingAppointments } from '@/store'
import { useTts } from '@/composables/useTts'
import { medicinesInSlot, nextMedicineSlot, slotStatuses } from '@/utils/schedule'
import { medicineSpeech } from '@/utils/speech'
import type { IconName } from '@/components/AppIcon.vue'

const props = defineProps<{ now: Date }>()
const router = useRouter()
const { speak } = useTts()

const meds = computed(() => activeMedicines(props.now))
const next = computed(() => nextMedicineSlot(props.now, meds.value))
const nextMeds = computed(() => (next.value ? medicinesInSlot(meds.value, next.value.slot.key) : []))
const statuses = computed(() => slotStatuses(props.now))
const appointments = computed(() => upcomingAppointments(props.now))

const nextLabel = computed(() => {
  if (!next.value) return ''
  const { slot, tomorrow } = next.value
  return `${tomorrow ? '明天 ' : ''}${slot.time} ${slot.name}`
})

const entries: { icon: IconName; title: string; subtitle: string; to: string }[] = [
  { icon: 'add-rx', title: '新增藥單', subtitle: '領藥後拍藥袋', to: '/elder/add' },
  { icon: 'my-rx', title: '我的藥單', subtitle: '看每一張藥單', to: '/elder/prescriptions' },
  { icon: 'calendar', title: '回診預約', subtitle: '北市聯醫各院區', to: '/elder/booking' },
  { icon: 'medical-card', title: '緊急醫療卡', subtitle: '緊急時讓救護人員看得到', to: '/elder/card' },
  { icon: 'invite', title: '邀請家屬', subtitle: '家屬也會收到用藥提醒', to: '/elder/invite' },
]
</script>

<template>
  <PageLayout>
    <GreetingBlock :now="now" />

    <section v-if="next" class="next-card" aria-labelledby="next-title">
      <div class="next-head">
        <h2 id="next-title" class="next-tag font-h3-semibold">下一次吃藥</h2>
        <span class="next-time font-h2-semibold">{{ nextLabel }}</span>
      </div>
      <MedicineCard
        v-for="m in nextMeds"
        :key="m.code"
        :medicine="m"
        :department="m.rx.department"
        show-department
        @click="router.push(`/elder/slot/${next.slot.key}`)"
        @speak="speak(medicineSpeech(m, true, state.lang), state.lang)"
      />
      <div class="read-row">
        <span class="read-label font-h3-regular">朗讀語言</span>
        <LanguageSwitch v-model="state.lang" />
      </div>
    </section>

    <h2 class="section-label">今天四個時段</h2>
    <div class="slots">
      <TimeSlotCard
        v-for="s in SLOTS"
        :key="s.key"
        :name="s.name"
        :time="s.time"
        :status="statuses[s.key]"
        :codes="medicinesInSlot(meds, s.key).map((m) => m.code)"
        @click="router.push(`/elder/slot/${s.key}`)"
      />
    </div>

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
  </PageLayout>
</template>

<style scoped>
.next-card {
  display: flex;
  flex-direction: column;
  gap: 12px;
  padding: 16px;
  border-radius: 12px;
  background: var(--color-primary-50);
}
.next-head {
  display: flex;
  align-items: baseline;
  flex-wrap: wrap;
  gap: 8px 12px;
}
.next-tag {
  color: var(--color-primary-700);
}
.next-time {
  color: var(--text-primary);
}
.read-row {
  display: flex;
  align-items: center;
  justify-content: space-between;
  flex-wrap: wrap;
  gap: 12px;
}
.slots {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(150px, 1fr));
  gap: 12px;
}
</style>
