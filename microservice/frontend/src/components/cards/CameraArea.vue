<script setup lang="ts">
/** 相機區共用骨架（EL-CRD-06 拍照／EL-CRD-07 掃描）：深色底、相機即時畫面、對準框、提示文字 */
import { ref } from 'vue'
import { useCamera } from '@/composables/useCamera'

withDefaults(defineProps<{ hint: string; frameWidth?: number; frameHeight?: number }>(), {
  frameWidth: 260,
  frameHeight: 300,
})

const video = ref<HTMLVideoElement | null>(null)
const { error, ready } = useCamera(video)

defineExpose({ video, ready })
</script>

<template>
  <section class="camera-area">
    <video ref="video" class="video" :class="{ on: ready }" playsinline muted aria-hidden="true" />
    <div class="overlay">
      <div class="center">
        <div
          class="frame"
          :style="{ width: `${frameWidth}px`, aspectRatio: `${frameWidth} / ${frameHeight}` }"
          aria-hidden="true"
        />
        <p class="hint font-h3-semibold">{{ error || hint }}</p>
        <slot />
      </div>
      <!-- 拍照按鈕等操作放在相機區最下方 -->
      <div v-if="$slots.bottom" class="bottom">
        <slot name="bottom" />
      </div>
    </div>
  </section>
</template>

<style scoped>
.camera-area {
  position: relative;
  flex: 1 1 auto;
  width: 100%;
  min-height: 460px;
  border-radius: 16px;
  overflow: hidden;
  background: var(--color-grey-900);
  display: flex;
  flex-direction: column;
}
.video {
  position: absolute;
  inset: 0;
  width: 100%;
  height: 100%;
  object-fit: cover;
  opacity: 0;
}
.video.on {
  opacity: 1;
}
.overlay {
  position: relative;
  flex: 1 1 auto;
  min-height: 460px;
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 24px;
  padding: 24px 16px 32px;
}
.center {
  flex: 1 1 auto;
  width: 100%;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  gap: 24px;
}
.bottom {
  flex: 0 0 auto;
  display: flex;
  justify-content: center;
}
.frame {
  /* 窄螢幕時等比例縮小，維持框框形狀 */
  max-width: 100%;
  height: auto;
  border-radius: 12px;
  border: 3px solid var(--color-primary-300);
}
.hint {
  color: var(--color-white);
  text-align: center;
  text-shadow: 0 1px 2px rgb(0 0 0 / 60%);
}
</style>
