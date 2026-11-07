<script setup lang="ts">
/** EL-CRD-05 空白狀態卡 */
</script>

<template>
  <section class="el-crd-05">
    <!-- illustration_icon_phone_upload（裝飾圖） -->
    <svg width="160" height="160" viewBox="0 0 160 160" aria-hidden="true" focusable="false">
      <circle cx="80" cy="80" r="72" fill="#FFFFFF" />
      <rect x="52" y="28" width="56" height="100" rx="10" fill="#5AB4C5" />
      <rect x="58" y="38" width="44" height="76" rx="4" fill="#FFFFFF" />
      <path d="M80 98V62M66 76l14-14 14 14" stroke="#356C77" stroke-width="6" fill="none" stroke-linecap="round" stroke-linejoin="round" />
      <circle cx="80" cy="121" r="3" fill="#FFFFFF" />
    </svg>
    <h2 class="title font-h2-semibold">還沒有任何藥單</h2>
    <p class="desc font-h3-regular">領藥後，請藥師或家人幫您拍藥袋，時間到就會提醒您吃藥。</p>
  </section>
</template>

<style scoped>
.el-crd-05 {
  width: 100%;
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 12px;
  padding: 24px 16px;
  border-radius: 12px;
  background: var(--color-primary-50);
  text-align: center;
}
.title {
  color: var(--text-primary);
}
.desc {
  color: var(--text-second);
}
</style>
