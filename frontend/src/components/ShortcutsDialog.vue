<template>
  <el-dialog
    v-model="visible"
    title="键盘快捷键"
    width="460px"
    append-to-body
    class="shortcuts-dialog"
  >
    <p class="shortcuts-hint">按 <kbd>?</kbd> 随时打开本面板，按 <kbd>Esc</kbd> 关闭。</p>
    <div class="shortcut-groups">
      <section v-for="group in SHORTCUT_GROUPS" :key="group.title" class="shortcut-group">
        <h3>{{ group.title }}</h3>
        <ul>
          <li v-for="item in group.items" :key="item.keys">
            <span class="shortcut-label">{{ item.label }}</span>
            <kbd class="shortcut-keys">{{ item.keys }}</kbd>
          </li>
        </ul>
      </section>
    </div>
    <template #footer>
      <el-button type="primary" @click="visible = false">知道了</el-button>
    </template>
  </el-dialog>
</template>

<script setup lang="ts">
import { onMounted, onUnmounted, ref } from 'vue'
import { useRouter } from 'vue-router'
import { isTypingTarget, LEADER_KEY, resolveLeader, SHORTCUT_GROUPS } from '../utils/shortcuts'

const router = useRouter()
const visible = ref(false)

let leaderActive = false
let leaderTimer: number | undefined

const clearLeader = () => {
  leaderActive = false
  if (leaderTimer) {
    window.clearTimeout(leaderTimer)
    leaderTimer = undefined
  }
}

const onKeydown = (event: KeyboardEvent) => {
  // Leave browser/OS shortcuts and typing alone.
  if (event.metaKey || event.ctrlKey || event.altKey) return
  if (isTypingTarget(event.target)) return

  if (event.key === '?') {
    event.preventDefault()
    clearLeader()
    visible.value = true
    return
  }

  if (leaderActive) {
    const match = resolveLeader(event.key)
    clearLeader()
    if (match) {
      event.preventDefault()
      visible.value = false
      router.push(match.path)
    }
    return
  }

  if (event.key.toLowerCase() === LEADER_KEY) {
    leaderActive = true
    leaderTimer = window.setTimeout(clearLeader, 1200)
  }
}

onMounted(() => window.addEventListener('keydown', onKeydown))
onUnmounted(() => {
  window.removeEventListener('keydown', onKeydown)
  clearLeader()
})
</script>

<style scoped>
.shortcuts-hint {
  margin: 0 0 16px;
  font-size: 13px;
  color: var(--fv-text-2);
}

.shortcut-groups {
  display: flex;
  flex-direction: column;
  gap: 18px;
}

.shortcut-group h3 {
  margin: 0 0 8px;
  font-size: 11px;
  font-weight: 800;
  letter-spacing: 0.14em;
  text-transform: uppercase;
  color: var(--fv-text-3);
}

.shortcut-group ul {
  margin: 0;
  padding: 0;
  list-style: none;
  display: flex;
  flex-direction: column;
  gap: 2px;
}

.shortcut-group li {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 16px;
  padding: 8px 2px;
  border-bottom: 1px solid var(--fv-border);
}

.shortcut-group li:last-child {
  border-bottom: none;
}

.shortcut-label {
  font-size: 13.5px;
  color: var(--fv-text);
}

kbd {
  font-family: inherit;
  font-size: 12px;
  font-weight: 600;
  color: var(--fv-text-2);
  background: var(--fv-surface-2);
  border: 1px solid var(--fv-border);
  border-radius: 6px;
  padding: 2px 7px;
  white-space: nowrap;
}
</style>
