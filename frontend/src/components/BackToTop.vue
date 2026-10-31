<template>
  <transition name="btt">
    <button
      v-show="visible"
      class="back-to-top"
      type="button"
      aria-label="回到顶部"
      @click="scrollToTop"
    >
      <svg class="ring" viewBox="0 0 44 44" aria-hidden="true">
        <circle class="ring-track" cx="22" cy="22" :r="RADIUS" />
        <circle
          class="ring-progress"
          cx="22"
          cy="22"
          :r="RADIUS"
          :style="{ strokeDasharray: circumference, strokeDashoffset: dashOffset }"
        />
      </svg>
      <svg class="arrow" viewBox="0 0 24 24" aria-hidden="true">
        <path d="M12 5l-7 7h4v7h6v-7h4z" />
      </svg>
    </button>
  </transition>
</template>

<script setup lang="ts">
import { computed, onMounted, onUnmounted, ref } from 'vue'
import { computeScrollProgress } from '../utils/scroll'

const RADIUS = 19
const circumference = 2 * Math.PI * RADIUS

const visible = ref(false)
const progress = ref(0)
const reduceMotion = ref(false)

const dashOffset = computed(() => String(circumference * (1 - progress.value)))

const onScroll = () => {
  visible.value = window.scrollY > 420
  progress.value = computeScrollProgress(
    window.scrollY,
    document.documentElement.scrollHeight,
    window.innerHeight,
  )
}

const scrollToTop = () => {
  window.scrollTo({ top: 0, behavior: reduceMotion.value ? 'auto' : 'smooth' })
}

onMounted(() => {
  reduceMotion.value = window.matchMedia('(prefers-reduced-motion: reduce)').matches
  onScroll()
  window.addEventListener('scroll', onScroll, { passive: true })
  window.addEventListener('resize', onScroll, { passive: true })
})

onUnmounted(() => {
  window.removeEventListener('scroll', onScroll)
  window.removeEventListener('resize', onScroll)
})
</script>

<style scoped>
.back-to-top {
  position: fixed;
  right: 24px;
  bottom: 24px;
  z-index: 80;
  width: 46px;
  height: 46px;
  display: grid;
  place-items: center;
  border: 1px solid var(--fv-border);
  border-radius: 50%;
  background: var(--fv-surface);
  color: var(--fv-primary);
  cursor: pointer;
  box-shadow: var(--fv-shadow-md);
  transition:
    transform 0.2s ease,
    color 0.2s ease,
    border-color 0.2s ease;
}

.back-to-top:hover {
  transform: translateY(-2px);
  border-color: var(--fv-primary);
}

.ring {
  position: absolute;
  inset: 0;
  width: 100%;
  height: 100%;
  transform: rotate(-90deg);
}

.ring-track,
.ring-progress {
  fill: none;
  stroke-width: 2.5;
}

.ring-track {
  stroke: var(--fv-surface-3);
}

.ring-progress {
  stroke: var(--fv-primary);
  stroke-linecap: round;
  transition: stroke-dashoffset 0.1s linear;
}

.arrow {
  width: 20px;
  height: 20px;
  fill: currentColor;
}

.btt-enter-active,
.btt-leave-active {
  transition:
    opacity 0.18s ease,
    transform 0.18s ease;
}

.btt-enter-from,
.btt-leave-to {
  opacity: 0;
  transform: translateY(8px) scale(0.9);
}

@media (max-width: 620px) {
  .back-to-top {
    right: 16px;
    bottom: 16px;
    width: 42px;
    height: 42px;
  }
}
</style>
