<script setup lang="ts">
/** CM-CRD-05 明細列 InfoRow（標籤 110 固定寬、內容置右；showDivider 控制分隔線） */
withDefaults(defineProps<{ label: string; value: string; showDivider?: boolean }>(), { showDivider: true })
</script>

<template>
  <div class="cm-crd-05" :class="{ divider: showDivider }">
    <dt class="label font-h3-regular">{{ label }}</dt>
    <dd class="value font-h3-semibold"><slot>{{ value }}</slot></dd>
  </div>
</template>

<style scoped>
.cm-crd-05 {
  width: 100%;
  display: flex;
  gap: 12px;
  padding: 12px 0;
}
.divider {
  border-bottom: 1px solid var(--color-grey-100);
}
.label {
  flex: 0 0 110px;
  margin: 0;
  color: var(--text-second);
}
.value {
  flex: 1 1 auto;
  min-width: 0;
  margin: 0;
  text-align: right;
  color: var(--text-primary);
  overflow-wrap: anywhere;
}
</style>
