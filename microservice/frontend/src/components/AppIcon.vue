<script setup lang="ts">
/**
 * 圖示（inline SVG）。預設為裝飾性（aria-hidden），可點元件需在外層按鈕提供 aria-label。
 * 註：Figma 圖示為臨時網址尚未下載，先以同語意的簡易圖示代替，待設計師提供正式 SVG 後替換。
 */
export type IconName =
  | 'back'
  | 'chevron-right'
  | 'chevron-down'
  | 'speaker'
  | 'info'
  | 'warning'
  | 'check'
  | 'check-circle'
  | 'add-rx'
  | 'my-rx'
  | 'calendar'
  | 'medical-card'
  | 'invite'
  | 'person'
  | 'phone'
  | 'camera'
  | 'qrcode'
  | 'bell'
  | 'clock'
  | 'pill'
  | 'edit'

withDefaults(defineProps<{ name: IconName; size?: number; label?: string }>(), { size: 24 })
</script>

<template>
  <svg
    :width="size"
    :height="size"
    viewBox="0 0 24 24"
    fill="none"
    stroke="currentColor"
    stroke-width="2"
    stroke-linecap="round"
    stroke-linejoin="round"
    :aria-hidden="label ? undefined : 'true'"
    :role="label ? 'img' : undefined"
    :aria-label="label"
    focusable="false"
  >
    <template v-if="name === 'back'"><path d="M15 18l-6-6 6-6" /></template>
    <template v-else-if="name === 'chevron-right'"><path d="M9 6l6 6-6 6" /></template>
    <template v-else-if="name === 'chevron-down'"><path d="M6 9l6 6 6-6" /></template>
    <template v-else-if="name === 'speaker'">
      <path d="M11 5L6 9H3v6h3l5 4V5z" fill="currentColor" />
      <path d="M15.5 8.5a5 5 0 010 7" />
      <path d="M18.5 5.5a9 9 0 010 13" />
    </template>
    <template v-else-if="name === 'info'">
      <circle cx="12" cy="12" r="10" />
      <path d="M12 16v-5M12 8h.01" />
    </template>
    <template v-else-if="name === 'warning'">
      <path d="M10.3 3.9L1.8 18a2 2 0 001.7 3h17a2 2 0 001.7-3L13.7 3.9a2 2 0 00-3.4 0z" />
      <path d="M12 9v4M12 17h.01" />
    </template>
    <template v-else-if="name === 'check'"><path d="M5 12l5 5L20 7" /></template>
    <template v-else-if="name === 'check-circle'">
      <circle cx="12" cy="12" r="10" />
      <path d="M7.5 12l3 3 6-6" />
    </template>
    <template v-else-if="name === 'add-rx'">
      <rect x="5" y="3" width="14" height="18" rx="2" />
      <path d="M12 8v8M8 12h8" />
    </template>
    <template v-else-if="name === 'my-rx'">
      <rect x="5" y="3" width="14" height="18" rx="2" />
      <path d="M9 8h6M9 12h6M9 16h4" />
    </template>
    <template v-else-if="name === 'calendar'">
      <rect x="3" y="5" width="18" height="16" rx="2" />
      <path d="M16 3v4M8 3v4M3 10h18" />
    </template>
    <template v-else-if="name === 'medical-card'">
      <rect x="2" y="5" width="20" height="14" rx="2" />
      <path d="M12 9v6M9 12h6" />
    </template>
    <template v-else-if="name === 'invite'">
      <circle cx="9" cy="8" r="4" />
      <path d="M2 21v-1a6 6 0 016-6h2a6 6 0 016 6v1" />
      <path d="M19 8v6M16 11h6" />
    </template>
    <template v-else-if="name === 'person'">
      <circle cx="12" cy="8" r="4" />
      <path d="M4 21v-1a7 7 0 0116 0v1" />
    </template>
    <template v-else-if="name === 'phone'">
      <path
        d="M22 16.9v3a2 2 0 01-2.2 2 19.8 19.8 0 01-8.6-3.1 19.5 19.5 0 01-6-6A19.8 19.8 0 012.1 4.2 2 2 0 014.1 2h3a2 2 0 012 1.7c.1.9.4 1.8.7 2.7a2 2 0 01-.5 2.1L8 9.8a16 16 0 006 6l1.3-1.3a2 2 0 012.1-.4c.9.3 1.8.6 2.7.7a2 2 0 011.7 2z"
      />
    </template>
    <template v-else-if="name === 'camera'">
      <path d="M23 19a2 2 0 01-2 2H3a2 2 0 01-2-2V8a2 2 0 012-2h4l2-3h6l2 3h4a2 2 0 012 2z" />
      <circle cx="12" cy="13" r="4" />
    </template>
    <template v-else-if="name === 'qrcode'">
      <rect x="3" y="3" width="7" height="7" />
      <rect x="14" y="3" width="7" height="7" />
      <rect x="3" y="14" width="7" height="7" />
      <path d="M14 14h3v3h-3zM20 14v.01M14 20h.01M17 20h4v-3" />
    </template>
    <template v-else-if="name === 'bell'">
      <path d="M18 8a6 6 0 00-12 0c0 7-3 9-3 9h18s-3-2-3-9" />
      <path d="M13.7 21a2 2 0 01-3.4 0" />
    </template>
    <template v-else-if="name === 'clock'">
      <circle cx="12" cy="12" r="10" />
      <path d="M12 6v6l4 2" />
    </template>
    <template v-else-if="name === 'pill'">
      <rect x="2" y="8" width="20" height="8" rx="4" transform="rotate(-45 12 12)" />
      <path d="M8.5 8.5l7 7" />
    </template>
    <template v-else-if="name === 'edit'">
      <path d="M12 20h9" />
      <path d="M16.5 3.5a2.1 2.1 0 013 3L7 19l-4 1 1-4z" />
    </template>
  </svg>
</template>
