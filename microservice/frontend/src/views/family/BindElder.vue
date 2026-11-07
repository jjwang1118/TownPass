<script setup lang="ts">
/** FM-PG-02 家屬：輸入邀請碼（含錯誤狀態 F02b）；表單與 EL-PG-17「綁定長輩」分頁共用 */
import PageLayout from '@/components/PageLayout.vue'
import BindElderForm from '@/views/shared/BindElderForm.vue'
</script>

<template>
  <PageLayout title="綁定長輩" fallback="/family">
    <BindElderForm />
  </PageLayout>
</template>
