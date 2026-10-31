<template>
  <div class="not-found">
    <div class="orb orb-a" aria-hidden="true"></div>
    <div class="orb orb-b" aria-hidden="true"></div>

    <div class="nf-card">
      <span class="brand-mark">FV</span>
      <p class="nf-code gradient-text">404</p>
      <h1>这块页面走丢了</h1>
      <p class="nf-sub">地址可能已经变更，或链接已经失效。回到首页，继续你的训练。</p>
      <div class="nf-actions">
        <el-button type="primary" size="large" @click="goHome">
          <el-icon><HomeFilled /></el-icon>
          返回首页
        </el-button>
        <el-button size="large" @click="goBack">返回上一页</el-button>
      </div>
      <p class="nf-tip">提示：按 <kbd>Ctrl / ⌘ + K</kbd> 搜索动作或页面。</p>
    </div>
  </div>
</template>

<script setup lang="ts">
import { useRouter } from 'vue-router'
import { HomeFilled } from '@element-plus/icons-vue'

const router = useRouter()

const goHome = () => router.push('/')

const goBack = () => {
  if (window.history.length > 1) router.back()
  else router.push('/')
}
</script>

<style scoped>
.not-found {
  position: relative;
  min-height: 100vh;
  display: flex;
  align-items: center;
  justify-content: center;
  padding: 24px;
  overflow: hidden;
}

.orb {
  position: absolute;
  border-radius: 50%;
  filter: blur(8px);
  opacity: 0.5;
  pointer-events: none;
}

.orb-a {
  width: 320px;
  height: 320px;
  top: -80px;
  left: -60px;
  background: radial-gradient(circle, rgba(194, 65, 12, 0.32), transparent 70%);
}

.orb-b {
  width: 360px;
  height: 360px;
  right: -100px;
  bottom: -120px;
  background: radial-gradient(circle, rgba(6, 182, 212, 0.4), transparent 70%);
}

.nf-card {
  position: relative;
  z-index: 1;
  max-width: 460px;
  width: 100%;
  padding: 40px 36px;
  text-align: center;
  background: var(--fv-surface);
  border: 1px solid var(--fv-border);
  border-radius: var(--fv-radius-xl);
  box-shadow: var(--fv-shadow-lg);
}

.brand-mark {
  display: inline-grid;
  place-items: center;
  width: 44px;
  height: 44px;
  border-radius: 14px;
  background: var(--fv-gradient);
  color: #fff;
  font-size: 15px;
  font-weight: 900;
  letter-spacing: -0.04em;
  box-shadow: var(--fv-shadow-glow);
}

.nf-code {
  margin: 18px 0 6px;
  font-size: 76px;
  font-weight: 900;
  line-height: 1;
  letter-spacing: -0.05em;
}

.nf-card h1 {
  margin: 0 0 10px;
  font-size: 22px;
  font-weight: 800;
  letter-spacing: -0.02em;
  color: var(--fv-text);
}

.nf-sub {
  margin: 0 auto 26px;
  max-width: 340px;
  font-size: 14px;
  line-height: 1.6;
  color: var(--fv-text-2);
}

.nf-actions {
  display: flex;
  gap: 12px;
  justify-content: center;
  flex-wrap: wrap;
}

.nf-tip {
  margin: 22px 0 0;
  font-size: 12px;
  color: var(--fv-text-3);
}

kbd {
  font-family: inherit;
  font-size: 11px;
  font-weight: 600;
  padding: 2px 6px;
  border: 1px solid var(--fv-border);
  border-radius: 5px;
  background: var(--fv-surface-2);
}
</style>
