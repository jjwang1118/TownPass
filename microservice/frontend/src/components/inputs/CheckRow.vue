<script setup lang="ts">
/** EL-CHK-01 核對勾選列 */
import AppIcon from '@/components/AppIcon.vue'

const checked = defineModel<boolean>({ required: true })
defineProps<{ describedBy?: string }>()
</script>

<template>
  <button
    type="button"
    role="checkbox"
    class="el-chk-01"
    :aria-checked="checked"
    :aria-describedby="describedBy"
    @click="checked = !checked"
  >
    <span class="box" :class="{ on: checked }">
      <AppIcon v-if="checked" name="check" :size="18" />
    </span>
    <span class="text font-h3-regular"><slot /></span>
  </button>
</template>

<style scoped>
.el-chk-01 {
  width: 100%;
  min-height: 48px;
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 12px 0;
  text-align: left;
  background: transparent;
}
.box {
  flex: 0 0 24px;
  width: 24px;
  height: 24px;
  border-radius: 4px;
  border: 2px solid var(--color-grey-400);
  display: flex;
  align-items: center;
  justify-content: center;
  color: var(--color-white);
}
.box.on {
  border-color: var(--color-primary-500);
  background: var(--color-primary-500);
}
.text {
  flex: 1 1 auto;
  color: var(--text-primary);
}
</style>
