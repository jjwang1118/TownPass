<script setup lang="ts">
/** EL-CRD-13 已綁定家屬卡片 */
import AppIcon from '@/components/AppIcon.vue'

defineProps<{ name: string; relation: string }>()
const emit = defineEmits<{ unbind: [] }>()
</script>

<template>
  <article class="el-crd-13">
    <span class="icon"><AppIcon name="person" /></span>
    <span class="texts">
      <span class="name font-h3-semibold">{{ name }}（{{ relation }}）</span>
      <span class="desc font-h3-regular">收到用藥與回診提醒</span>
    </span>
    <button type="button" class="unbind font-h3-regular" :aria-label="`取消綁定 ${name}`" @click="emit('unbind')">
      取消綁定
    </button>
  </article>
</template>

<style scoped>
.el-crd-13 {
  width: 100%;
  display: flex;
  align-items: center;
  flex-wrap: wrap;
  gap: 12px;
  padding: 16px;
  border-radius: 12px;
  border: 1px solid var(--color-grey-200);
}
.icon {
  flex: 0 0 48px;
  width: 48px;
  height: 48px;
  border-radius: 24px;
  background: var(--color-primary-50);
  color: var(--color-primary-700);
  display: flex;
  align-items: center;
  justify-content: center;
}
.texts {
  flex: 1 1 140px;
  display: flex;
  flex-direction: column;
  gap: 2px;
}
.name {
  color: var(--text-primary);
}
.desc {
  color: var(--text-second);
}
.unbind {
  min-height: 48px;
  padding: 8px 12px;
  border-radius: 8px;
  border: 1px solid var(--color-grey-300);
  color: var(--text-second);
}
</style>
