<script setup lang="ts">
/** 時段用藥詳情共用版面：EL-PG-03（長者）／FM-PG-04（家屬） */
import { computed } from 'vue'
import { useRoute } from 'vue-router'
import PageLayout from '@/components/PageLayout.vue'
import ReadAloudButton from '@/components/buttons/ReadAloudButton.vue'
import LanguageSwitch from '@/components/segments/LanguageSwitch.vue'
import MedicineCard from '@/components/cards/MedicineCard.vue'
import InfoNotice from '@/components/alerts/InfoNotice.vue'
import { SLOT_BY_KEY } from '@/data/constants'
import { activeMedicines, state } from '@/store'
import { useNow } from '@/composables/useNow'
import { useTts } from '@/composables/useTts'
import { groupByPrescription, medicinesInSlot } from '@/utils/schedule'
import { medicineSpeech, slotSpeech } from '@/utils/speech'
import type { SlotKey } from '@/types'

const props = defineProps<{ titlePrefix?: string; notice: string; fallback: string }>()

const route = useRoute()
const now = useNow()
const { speak } = useTts()

const slot = computed(() => SLOT_BY_KEY[route.params.slot as SlotKey] ?? SLOT_BY_KEY.morning)
const meds = computed(() => medicinesInSlot(activeMedicines(now.value), slot.value.key))
const groups = computed(() => groupByPrescription(meds.value))
const heading = computed(
  () => `${props.titlePrefix ? `${props.titlePrefix} ` : ''}${slot.value.name} ${slot.value.time} 要吃的藥`,
)
</script>

<template>
  <PageLayout title="用藥詳情" :fallback="fallback">
    <h2 class="page-heading">{{ heading }}</h2>
    <div class="read-row">
      <ReadAloudButton @click="speak(slotSpeech(heading, meds), state.lang)" />
      <LanguageSwitch v-model="state.lang" />
    </div>

    <template v-for="g in groups" :key="g.rx.code">
      <h3 class="group-label font-h3-semibold">{{ g.rx.code }}　{{ g.rx.department ? `${g.rx.department}｜${g.rx.hospital}` : g.rx.hospital }}</h3>
      <MedicineCard
        v-for="m in g.medicines"
        :key="m.code"
        :medicine="m"
        :clickable="false"
        @speak="speak(medicineSpeech(m), state.lang)"
      />
    </template>
    <p v-if="meds.length === 0" class="page-desc">這個時段不用吃藥。</p>

    <div class="flex-spacer" />
    <InfoNotice>{{ notice }}</InfoNotice>
  </PageLayout>
</template>

<style scoped>
.read-row {
  display: flex;
  align-items: center;
  justify-content: space-between;
  flex-wrap: wrap;
  gap: 12px;
}
.group-label {
  color: var(--text-second);
}
</style>
