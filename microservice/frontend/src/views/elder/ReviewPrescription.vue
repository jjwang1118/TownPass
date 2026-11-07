<script setup lang="ts">
/** EL-PG-07 長者：確認藥單（核對中）；全部勾選後 → EL-PG-08 */
import { useRouter } from 'vue-router'
import PrescriptionReview from '@/views/shared/PrescriptionReview.vue'

const router = useRouter()
</script>

<template>
  <PrescriptionReview mode="review" @submit="router.push('/elder/add/confirm')" />
</template>
