<script setup lang="ts">
/**
 * EL-PG-17 長者：家人綁定（邀請家屬／綁定長輩）
 * - 上方切換「邀請家屬／綁定長輩」（網址 ?tab=bind）
 * - 邀請家屬：邀請碼 6 碼數字，10 分鐘後失效；「換一組數字」立即重新產生並重新計時；
 *   取消綁定 → EL-MD-01 確認彈窗
 * - 綁定長輩：長輩用自己的帳號輸入另一位長輩的邀請碼（長輩之間可以互相綁定，不能綁定自己）；
 *   下方「我關心的長輩」點「查看」→ 沿用家屬頁面 FM-PG-03 查看對方的用藥
 */
import { computed, onMounted, ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import PageLayout from '@/components/PageLayout.vue'
import TabSwitch from '@/components/segments/TabSwitch.vue'
import NoticeBox from '@/components/alerts/NoticeBox.vue'
import BindElderForm from '@/views/shared/BindElderForm.vue'
import InviteCodeCard from '@/components/cards/InviteCodeCard.vue'
import FamilyMemberCard from '@/components/cards/FamilyMemberCard.vue'
import SecondaryButton from '@/components/buttons/SecondaryButton.vue'
import UnbindDialog from '@/components/overlays/UnbindDialog.vue'
import { ensureInviteValid, regenerateInvite, state, unbindFamily, viewCaredElder } from '@/store'
import { useNow } from '@/composables/useNow'
import type { FamilyMember } from '@/types'

type Tab = 'invite' | 'bind'
const TABS: { value: Tab; label: string }[] = [
  { value: 'invite', label: '邀請家屬' },
  { value: 'bind', label: '綁定長輩' },
]
const route = useRoute()
const router = useRouter()
const tab = computed<Tab>({
  get: () => (route.query.tab === 'bind' ? 'bind' : 'invite'),
  set: (v) => {
    justBound.value = false
    router.replace({ query: v === 'bind' ? { tab: 'bind' } : {} })
  },
})

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

const justBound = ref(false)

function view(bindingId: string) {
  viewCaredElder(bindingId)
  router.push('/family/home')
}
</script>

<template>
  <PageLayout title="家人綁定" fallback="/elder">
    <TabSwitch v-model="tab" :options="TABS" label="邀請家屬或綁定長輩" />

    <template v-if="tab === 'bind'">
      <BindElderForm as-elder @bound="justBound = true">
        <NoticeBox v-if="justBound" live>綁定成功！可以在下方查看對方的用藥。</NoticeBox>
      </BindElderForm>

      <h2 class="section-label">我關心的長輩</h2>
      <FamilyMemberCard
        v-for="c in state.caredElders"
        :key="c.id"
        :name="c.name"
        desc="可以查看用藥與緊急醫療卡"
        action-text="查看"
        @action="view(c.id)"
      />
      <p v-if="state.caredElders.length === 0" class="page-desc">目前還沒有綁定其他長輩。</p>
    </template>

    <template v-else>
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
        @action="pending = f"
      />
      <p v-if="state.families.length === 0" class="page-desc">目前還沒有綁定的家屬。</p>

      <UnbindDialog
        :open="pending !== null"
        :family-name="pending ? `${pending.name}（${pending.relation}）` : ''"
        @close="pending = null"
        @confirm="confirmUnbind"
      />
    </template>
  </PageLayout>
</template>
