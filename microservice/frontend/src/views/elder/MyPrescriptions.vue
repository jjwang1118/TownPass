<script setup lang="ts">
/** EL-PG-18 長者：我的藥單（吃藥中／已吃完，組內依看診日期新到舊） */
import { computed } from 'vue'
import { useRouter } from 'vue-router'
import PageLayout from '@/components/PageLayout.vue'
import PrescriptionRow from '@/components/cards/PrescriptionRow.vue'
import PrimaryButton from '@/components/buttons/PrimaryButton.vue'
import { daysLeft, isFinished, state } from '@/store'
import { formatMonthDay } from '@/utils/date'

const router = useRouter()
const now = new Date()

const sorted = computed(() => [...state.prescriptions].sort((a, b) => b.visitDate.localeCompare(a.visitDate)))
const active = computed(() => sorted.value.filter((rx) => !isFinished(rx, now)))
const finished = computed(() => sorted.value.filter((rx) => isFinished(rx, now)))
</script>

<template>
  <PageLayout title="我的藥單" fallback="/elder">
    <h2 class="section-label">吃藥中</h2>
    <PrescriptionRow
      v-for="rx in active"
      :key="`${rx.code}-${rx.visitDate}`"
      :code="rx.code"
      :hospital="rx.hospital"
      :department="rx.department"
      :status-text="`${formatMonthDay(rx.visitDate)} 看診｜還剩 ${daysLeft(rx, now)} 天`"
      :finished="false"
    />
    <p v-if="active.length === 0" class="page-desc">目前沒有吃藥中的藥單。</p>

    <template v-if="finished.length">
      <h2 class="section-label">已吃完</h2>
      <PrescriptionRow
        v-for="rx in finished"
        :key="`${rx.code}-${rx.visitDate}`"
        :code="rx.code"
        :hospital="rx.hospital"
        :department="rx.department"
        :status-text="`${formatMonthDay(rx.visitDate)} 看診｜已吃完`"
        finished
      />
    </template>

    <PrimaryButton @click="router.push('/elder/add')">新增藥單</PrimaryButton>
  </PageLayout>
</template>
