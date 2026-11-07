<script setup lang="ts">
/** CM-CRD-05 的列表容器（語意為 description list） */
import InfoRow from './InfoRow.vue'

defineProps<{ rows: { label: string; value: string }[]; label?: string }>()
</script>

<template>
  <dl class="info-list" :aria-label="label">
    <InfoRow
      v-for="(row, i) in rows"
      :key="`${row.label}-${i}`"
      :label="row.label"
      :value="row.value"
      :show-divider="i < rows.length - 1"
    />
  </dl>
</template>

<style scoped>
.info-list {
  width: 100%;
  margin: 0;
  display: flex;
  flex-direction: column;
}
</style>
