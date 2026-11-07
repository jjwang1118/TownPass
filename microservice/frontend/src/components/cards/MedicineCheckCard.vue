<script setup lang="ts">
/** EL-CRD-09 藥品核對卡：點卡片或「編輯」→ 修改藥品；單顆朗讀不冒泡 */
import AppIcon from '@/components/AppIcon.vue'
import ReadAloudButton from '@/components/buttons/ReadAloudButton.vue'
import RxBadge from './RxBadge.vue'
import { amountText, slotNames } from '@/utils/schedule'
import type { Medicine } from '@/types'

defineProps<{ medicine: Medicine; id?: string }>()
const emit = defineEmits<{ edit: []; speak: [] }>()
</script>

<template>
  <article :id="id" class="el-crd-09">
    <div class="row">
      <button type="button" class="main" :aria-label="`修改 ${medicine.code} ${medicine.name}`" @click="emit('edit')">
        <span class="top">
          <RxBadge :code="medicine.code" />
          <span class="amount font-h2-semibold">{{ amountText(medicine.amount) }}</span>
        </span>
        <span class="name font-h3-regular">{{ medicine.name }}</span>
        <span class="meta font-h3-regular">{{ medicine.effect }}｜{{ slotNames(medicine.slots) }}</span>
      </button>
      <ReadAloudButton variant="single" :label="`朗讀 ${medicine.code} ${medicine.name}`" @click="emit('speak')" />
    </div>
    <div class="edit-row">
      <button type="button" class="edit font-h3-semibold" @click.stop="emit('edit')">
        <AppIcon name="edit" :size="20" />
        編輯
      </button>
    </div>
  </article>
</template>

<style scoped>
.el-crd-09 {
  width: 100%;
  display: flex;
  flex-direction: column;
  gap: 12px;
  padding: 16px;
  border-radius: 12px;
  border: 1px solid var(--color-grey-200);
  background: var(--background-color);
}
.row {
  display: flex;
  align-items: flex-start;
  gap: 8px;
}
.main {
  flex: 1 1 auto;
  min-width: 0;
  display: flex;
  flex-direction: column;
  gap: 2px;
  text-align: left;
}
.top {
  display: flex;
  align-items: center;
  gap: 12px;
  margin-bottom: 6px;
}
.amount,
.name {
  color: var(--text-primary);
}
.meta {
  color: var(--text-second);
}
.edit-row {
  display: flex;
  justify-content: flex-end;
}
.edit {
  min-height: 48px;
  min-width: 48px;
  padding: 0 12px;
  display: inline-flex;
  align-items: center;
  gap: 4px;
  color: var(--color-primary-700);
}
</style>
