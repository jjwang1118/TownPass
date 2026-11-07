<script setup lang="ts">
/**
 * EL-INP-02 藥名搜尋（後端 GET /drugs/search，資料為健保用藥品項 4.5 萬筆）
 * - 輸入 2 個字以上即時比對字首（中英文、不分大小寫），比對字加粗
 * - 最多 8 筆，北市聯醫常用藥排前面；同藥名只出現一次，選到的劑量帶入健保藥品代號
 * - 藥名必須從清單點選
 */
import { computed, ref, watch } from 'vue'
import TextField from './TextField.vue'
import { get } from '@/api/client'
import { toDrugEntry } from '@/api/mappers'
import type { DrugSearchItem } from '@/api/types'
import type { DrugEntry } from '@/types'

const props = defineProps<{ selected: string; errorText?: string }>()
const emit = defineEmits<{ select: [drug: DrugEntry] }>()

const query = ref(props.selected)
const picked = ref(!!props.selected)
/** 最近一次從清單選定（或初始帶入）的文字 */
let pickedText = props.selected

const found = ref<DrugEntry[]>([])
const searching = ref(false)
let timer = 0
let latest = ''

watch(query, (q) => {
  // 使用者修改文字後，需重新從清單選擇
  if (q !== pickedText) picked.value = false
  window.clearTimeout(timer)
  const text = q.trim()
  if (picked.value || text.length < 2) {
    found.value = []
    return
  }
  // 停止打字 250 毫秒後才查詢，避免每打一個字就送一次
  timer = window.setTimeout(async () => {
    latest = text
    searching.value = true
    try {
      const items = await get<DrugSearchItem[]>('/drugs/search', { role: 'elder', query: { q: text } })
      if (latest === text) found.value = items.map(toDrugEntry)
    } catch {
      if (latest === text) found.value = []
    } finally {
      if (latest === text) searching.value = false
    }
  }, 250)
})

interface Match {
  drug: DrugEntry
  display: string
  matchLen: number
}

const results = computed<Match[]>(() => {
  const q = query.value.trim()
  if (picked.value || q.length < 2) return []
  // 後端已依字首比對並排序（常用藥在前）；字首不在藥名開頭（例如比對到主成分）時不加粗
  return found.value.map((drug) => ({
    drug,
    display: drug.zh ? `${drug.name}（${drug.zh}）` : drug.name,
    matchLen: drug.name.toLowerCase().startsWith(q.toLowerCase()) ? q.length : 0,
  }))
})

const showNotFound = computed(
  () => !picked.value && !searching.value && query.value.trim().length >= 2 && results.value.length === 0,
)

/** 回傳 [加粗字, 其餘字]；中文字首比對時加粗中文部分 */
function split(m: Match): { before: string; bold: string; after: string } {
  const q = query.value.trim()
  if (m.drug.name.toLowerCase().startsWith(q.toLowerCase())) {
    return { before: '', bold: m.display.slice(0, m.matchLen), after: m.display.slice(m.matchLen) }
  }
  const idx = m.display.indexOf(q)
  if (idx < 0) return { before: m.display, bold: '', after: '' }
  return { before: m.display.slice(0, idx), bold: q, after: m.display.slice(idx + q.length) }
}

function choose(m: Match) {
  pickedText = m.drug.name
  query.value = m.drug.name
  picked.value = true
  emit('select', m.drug)
}
</script>

<template>
  <div class="el-inp-02">
    <TextField
      v-model="query"
      label="藥名（英文或中文都可以）"
      required
      placeholder="輸入藥袋上的英文或中文藥名"
      help-text="例如：Asp 或 阿斯"
      :error-text="errorText"
      inputmode="search"
    />
    <p v-if="results.length" class="count font-h3-regular" role="status">找到 {{ results.length }} 個藥名</p>
    <ul v-if="results.length" class="results">
      <li v-for="m in results" :key="m.drug.name">
        <button type="button" class="result" @click="choose(m)">
          <span class="name font-h3-regular">
            {{ split(m).before }}<strong class="hit">{{ split(m).bold }}</strong>{{ split(m).after }}
          </span>
          <span class="meta font-h3-regular">有 {{ m.drug.doses.length }} 種劑量｜{{ m.drug.source }}</span>
        </button>
      </li>
    </ul>
    <p v-if="showNotFound" class="not-found font-h3-regular" role="status">
      找不到這個藥名，請重新輸入，或重新拍藥袋。
    </p>
  </div>
</template>

<style scoped>
.el-inp-02 {
  width: 100%;
  display: flex;
  flex-direction: column;
  gap: 12px;
}
.count,
.not-found {
  color: var(--text-second);
}
.results {
  list-style: none;
  margin: 0;
  padding: 0;
  display: flex;
  flex-direction: column;
  gap: 8px;
}
.result {
  width: 100%;
  min-height: 48px;
  display: flex;
  flex-direction: column;
  gap: 2px;
  padding: 12px 16px;
  border-radius: 12px;
  border: 1px solid var(--color-grey-200);
  background: var(--background-color);
  text-align: left;
}
.name {
  color: var(--text-primary);
}
.hit {
  color: var(--color-primary-700);
  font-weight: 700;
}
.meta {
  color: var(--text-second);
}
</style>
