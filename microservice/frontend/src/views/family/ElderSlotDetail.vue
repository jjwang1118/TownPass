<script setup lang="ts">
/** FM-PG-04 家屬：長輩用藥詳情（只能查看，藥品卡不可點） */
import SlotDetail from '@/views/shared/SlotDetail.vue'
import { state } from '@/store'
</script>

<template>
  <SlotDetail :title-prefix="state.elder.name" notice="家屬只能查看，不能修改長輩的藥單。" fallback="/family/home" />
</template>
