<script setup lang="ts">
/** 長者首頁：有藥 → EL-PG-01；尚無任何藥單 → EL-PG-02 */
import { computed } from 'vue'
import { activePrescriptions } from '@/store'
import { useNow } from '@/composables/useNow'
import HomeWithMedicine from './HomeWithMedicine.vue'
import HomeEmpty from './HomeEmpty.vue'

const now = useNow()
const hasMedicine = computed(() => activePrescriptions(now.value).length > 0)
</script>

<template>
  <HomeWithMedicine v-if="hasMedicine" :now="now" />
  <HomeEmpty v-else :now="now" />
</template>
