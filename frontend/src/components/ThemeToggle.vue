<template>
  <el-dropdown trigger="click" @command="setMode">
    <button
      class="theme-toggle"
      type="button"
      aria-label="切换主题"
      :title="resolved === 'dark' ? '切换到浅色主题' : '切换到深色主题'"
    >
      <el-icon>
        <Sunny v-if="resolved === 'dark'" />
        <Moon v-else />
      </el-icon>
    </button>
    <template #dropdown>
      <el-dropdown-menu class="theme-menu">
        <el-dropdown-item command="light" :class="{ 'is-current': mode === 'light' }">
          <el-icon><Sunny /></el-icon>浅色
        </el-dropdown-item>
        <el-dropdown-item command="dark" :class="{ 'is-current': mode === 'dark' }">
          <el-icon><Moon /></el-icon>深色
        </el-dropdown-item>
        <el-dropdown-item command="system" :class="{ 'is-current': mode === 'system' }">
          <el-icon><Monitor /></el-icon>跟随系统
        </el-dropdown-item>
      </el-dropdown-menu>
    </template>
  </el-dropdown>
</template>

<script setup lang="ts">
import { Monitor, Moon, Sunny } from '@element-plus/icons-vue'
import { useTheme } from '../composables/useTheme'

const { mode, resolved, setMode } = useTheme()
</script>

<style scoped>
.theme-toggle {
  width: 38px;
  height: 38px;
  border-radius: 12px;
  border: 1px solid var(--fv-border);
  background: var(--fv-surface);
  color: var(--fv-text-2);
  display: inline-flex;
  align-items: center;
  justify-content: center;
  cursor: pointer;
  transition:
    color 0.2s ease,
    background 0.2s ease,
    transform 0.2s ease;
}

.theme-toggle:hover {
  color: var(--fv-primary);
  background: var(--fv-primary-soft);
  transform: translateY(-1px);
}

.theme-menu :deep(.el-dropdown-menu__item.is-current) {
  color: var(--fv-primary);
  font-weight: 700;
}
</style>
