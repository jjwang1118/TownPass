<script setup lang="ts">
/**
 * EL-PG-17 長者：邀請家屬
 * - 邀請碼 6 碼數字，10 分鐘後失效；「換一組數字」立即重新產生並重新計時
 * - 取消綁定 → EL-MD-01 確認彈窗
 */
import { computed, onMounted, ref } from 'vue'
import PageLayout from '@/components/PageLayout.vue'
import InviteCodeCard from '@/components/cards/InviteCodeCard.vue'
import FamilyMemberCard from '@/components/cards/FamilyMemberCard.vue'
import SecondaryButton from '@/components/buttons/SecondaryButton.vue'
import UnbindDialog from '@/components/overlays/UnbindDialog.vue'
import { ensureInviteValid, regenerateInvite, state, unbindFamily } from '@/store'
import { useNow } from '@/composables/useNow'
import type { FamilyMember } from '@/types'

const now = useNow(5_000)

onMounted(ensureInviteValid)

const remainingMin = computed(() => Math.ceil((state.invite.expiresAt - now.value.getTime()) / 60_000))
const validText = computed(() =>
  remainingMin.value > 0 ? `${remainingMin.value} 分鐘內有效` : '這組數字已失效，請按「換一組數字」',
)

const pending = ref<FamilyMember | null>(null)

function confirmUnbind() {
  if (pending.value) unbindFamily(pending.value.id)
  pending.value = null
}
</script>

<template>
  <PageLayout title="邀請家屬" fallback="/elder">
    <h2 class="page-heading">請家屬輸入這組數字</h2>
    <p class="page-desc">家屬在自己手機的「呷藥囉」輸入後，就會收到您的用藥和回診提醒。</p>
    <InviteCodeCard :code="state.invite.code" :valid-text="validText" />
    <SecondaryButton @click="regenerateInvite">換一組數字</SecondaryButton>

    <h2 class="section-label">已綁定的家屬</h2>
    <FamilyMemberCard
      v-for="f in state.families"
      :key="f.id"
      :name="f.name"
      :relation="f.relation"
      @unbind="pending = f"
    />
    <p v-if="state.families.length === 0" class="page-desc">目前還沒有綁定的家屬。</p>

    <UnbindDialog
      :open="pending !== null"
      :family-name="pending ? `${pending.name}（${pending.relation}）` : ''"
      @close="pending = null"
      @confirm="confirmUnbind"
    />
  </PageLayout>
</template>
