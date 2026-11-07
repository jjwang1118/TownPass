import { createRouter, createWebHashHistory, type RouteRecordRaw } from 'vue-router'
import { ensureElder, ensureFamily, state } from '@/store'

/**
 * 路由對應介面規格 ID（meta.id）。使用 hash 模式，部署在任意外部網址皆可直接載入。
 * 入口：/elder 長者、/family 家屬、/rescue 救護人員
 */
const routes: RouteRecordRaw[] = [
  { path: '/', redirect: '/elder' },

  /* ---------- 長者 ---------- */
  { path: '/elder', component: () => import('@/views/elder/ElderHome.vue'), meta: { id: 'EL-PG-01/02', title: '呷藥囉' } },
  { path: '/elder/slot/:slot', component: () => import('@/views/elder/SlotMedicineDetail.vue'), meta: { id: 'EL-PG-03', title: '用藥詳情' } },
  { path: '/elder/add', component: () => import('@/views/elder/AddPrescription.vue'), meta: { id: 'EL-PG-04', title: '新增藥單' } },
  { path: '/elder/add/photo', component: () => import('@/views/elder/PhotoPrescription.vue'), meta: { id: 'EL-PG-05', title: '拍藥袋' } },
  { path: '/elder/add/qr', component: () => import('@/views/elder/ScanPrescriptionQr.vue'), meta: { id: 'EL-PG-06', title: '掃描 QR Code' } },
  { path: '/elder/add/review', component: () => import('@/views/elder/ReviewPrescription.vue'), meta: { id: 'EL-PG-07', title: '確認藥單' } },
  { path: '/elder/add/confirm', component: () => import('@/views/elder/ConfirmPrescription.vue'), meta: { id: 'EL-PG-08', title: '確認藥單' } },
  { path: '/elder/add/medicine/:index', component: () => import('@/views/elder/EditMedicine.vue'), meta: { id: 'EL-PG-13', title: '修改藥品' } },
  { path: '/elder/add/manual', component: () => import('@/views/elder/ManualAddMedicine.vue'), meta: { id: 'EL-PG-14', title: '手動新增' } },
  { path: '/elder/booking', component: () => import('@/views/elder/BookingStart.vue'), meta: { id: 'EL-PG-09', title: '回診預約' } },
  { path: '/elder/booking/filled', component: () => import('@/views/elder/BookingFilled.vue'), meta: { id: 'EL-PG-10', title: '回診預約' } },
  { path: '/elder/booking/confirm', component: () => import('@/views/elder/BookingConfirm.vue'), meta: { id: 'EL-PG-11', title: '確認預約' } },
  { path: '/elder/booking/done', component: () => import('@/views/elder/BookingSuccess.vue'), meta: { id: 'EL-PG-12', title: '預約結果' } },
  { path: '/elder/card', component: () => import('@/views/elder/MyEmergencyCard.vue'), meta: { id: 'EL-PG-15', title: '緊急醫療卡' } },
  { path: '/elder/card/edit', component: () => import('@/views/elder/EditEmergencyCard.vue'), meta: { id: 'EL-PG-16', title: '編輯緊急醫療卡' } },
  { path: '/elder/invite', component: () => import('@/views/elder/InviteFamily.vue'), meta: { id: 'EL-PG-17', title: '邀請家屬' } },
  { path: '/elder/prescriptions/:index', component: () => import('@/views/elder/PrescriptionDetail.vue'), meta: { id: '藥單詳情', title: '藥單詳情' } },
  { path: '/elder/prescriptions',component: () => import('@/views/elder/MyPrescriptions.vue'), meta: { id: 'EL-PG-18', title: '我的藥單' } },

  /* ---------- 家屬 ---------- */
  { path: '/family', component: () => import('@/views/family/FamilyLogin.vue'), meta: { id: 'FM-PG-01', title: '呷藥囉' } },
  { path: '/family/bind', component: () => import('@/views/family/BindElder.vue'), meta: { id: 'FM-PG-02', title: '綁定長輩', familyAuth: true } },
  { path: '/family/home', component: () => import('@/views/family/FamilyHome.vue'), meta: { id: 'FM-PG-03', title: '呷藥囉', familyAuth: true, familyBound: true } },
  { path: '/family/slot/:slot', component: () => import('@/views/family/ElderSlotDetail.vue'), meta: { id: 'FM-PG-04', title: '用藥詳情', familyAuth: true, familyBound: true } },
  { path: '/family/card', component: () => import('@/views/family/ElderEmergencyCard.vue'), meta: { id: 'FM-PG-05', title: '緊急醫療卡', familyAuth: true, familyBound: true } },
  { path: '/family/notice', component: () => import('@/views/family/RescueViewNotice.vue'), meta: { id: 'FM-PG-06', title: '通知', familyAuth: true, familyBound: true } },

  /* ---------- 救護人員 ---------- */
  { path: '/rescue', component: () => import('@/views/rescue/RescueLogin.vue'), meta: { id: 'RE-PG-01', title: '救護人員專用' } },
  { path: '/rescue/search', component: () => import('@/views/rescue/SearchElder.vue'), meta: { id: 'RE-PG-02', title: '查詢緊急醫療卡', rescueAuth: true } },
  { path: '/rescue/card', component: () => import('@/views/rescue/RescueEmergencyCard.vue'), meta: { id: 'RE-PG-03', title: '緊急醫療卡', rescueAuth: true } },
  { path: '/rescue/closed', component: () => import('@/views/rescue/CardClosed.vue'), meta: { id: 'RE-PG-04', title: '查詢緊急醫療卡', rescueAuth: true } },

  { path: '/:pathMatch(.*)*', redirect: '/elder' },
]

export const router = createRouter({
  history: createWebHashHistory(),
  routes,
  scrollBehavior: (_to, _from, saved) => saved ?? { top: 0 },
})

router.beforeEach(async (to, from) => {
  // 長者：第一次進入時用台北通帳號登入並載入資料；回到首頁時重新讀取
  if (to.path.startsWith('/elder')) await ensureElder(to.path === '/elder' && from.path !== '/')
  // 家屬：已登入過就載入綁定長輩的資料；回到首頁時重新讀取（長輩可能剛新增藥單）
  if (to.meta.familyAuth) await ensureFamily(to.path === '/family/home')
  if (to.meta.familyAuth && !state.familyUser.loggedIn) return '/family'
  if (to.meta.familyBound && !state.familyUser.bound) return '/family/bind'
  if (to.meta.rescueAuth && !state.rescue) return '/rescue'
  return true
})

router.afterEach((to) => {
  const title = typeof to.meta.title === 'string' ? to.meta.title : '呷藥囉'
  document.title = title === '呷藥囉' ? title : `${title}｜呷藥囉`
})
