/**
 * 藥量計算：還剩幾天 = 剩下顆數 ÷ 每天吃幾顆
 * - 每天吃幾顆 = 一次幾顆 × 一天幾個時段
 * - 剩下顆數 = 總顆數 − 每天吃幾顆 × 從看診（領藥）日到今天過了幾天
 *   （目前沒有記錄實際服藥，假設都有按時吃）
 * - 藥單還剩幾天：取藥單內最晚吃完的藥（全部吃完才算整張藥單吃完）
 */
import type { Medicine } from '@/types'
import { diffDays, parseDate } from './date'

interface WithMedicines {
  visitDate: string
  medicines: Pick<Medicine, 'amount' | 'slots' | 'quantity'>[]
}

/** 每天吃幾顆 */
export function dailyAmount(m: Pick<Medicine, 'amount' | 'slots'>): number {
  return m.amount * m.slots.length
}

/** 這個藥總共可以吃幾天（總顆數 ÷ 每天吃幾顆） */
export function supplyDays(m: Pick<Medicine, 'amount' | 'slots' | 'quantity'>): number {
  const daily = dailyAmount(m)
  return daily > 0 ? Math.floor(m.quantity / daily) : 0
}

function elapsedDays(visitDate: string, now: Date): number {
  return Math.max(0, diffDays(parseDate(visitDate), now))
}

/** 剩下幾顆 */
export function pillsLeft(m: Pick<Medicine, 'amount' | 'slots' | 'quantity'>, visitDate: string, now: Date): number {
  return Math.max(0, m.quantity - dailyAmount(m) * elapsedDays(visitDate, now))
}

/** 這個藥還剩幾天（剩下顆數 ÷ 每天吃幾顆） */
export function medicineDaysLeft(
  m: Pick<Medicine, 'amount' | 'slots' | 'quantity'>,
  visitDate: string,
  now: Date,
): number {
  const daily = dailyAmount(m)
  return daily > 0 ? Math.floor(pillsLeft(m, visitDate, now) / daily) : 0
}

/** 整張藥單可以吃幾天（最久的那個藥） */
export function prescriptionSupplyDays(rx: Pick<WithMedicines, 'medicines'>): number {
  return Math.max(0, ...rx.medicines.map(supplyDays))
}

/** 整張藥單還剩幾天（最晚吃完的那個藥） */
export function prescriptionDaysLeft(rx: WithMedicines, now: Date): number {
  return Math.max(0, ...rx.medicines.map((m) => medicineDaysLeft(m, rx.visitDate, now)))
}
