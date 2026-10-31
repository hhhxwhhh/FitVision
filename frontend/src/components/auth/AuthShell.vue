<template>
  <div class="auth-shell">
    <div class="auth-glow auth-glow-a" aria-hidden="true"></div>
    <div class="auth-glow auth-glow-b" aria-hidden="true"></div>

    <aside class="auth-story">
      <router-link to="/" class="auth-brand">
        <span class="brand-mark">FV</span>
        <span class="brand-name">FitVision</span>
      </router-link>

      <div class="story-copy">
        <span class="story-eyebrow">AI-POWERED FITNESS COACH</span>
        <h1>
          让每一次<br />
          <span class="gradient-text">动作都算数。</span>
        </h1>
        <p>
          实时姿态识别、视觉大模型纠错与混合推荐，把专业教练的判断带进你的每一次训练。
        </p>

        <ul class="story-features">
          <li>
            <span class="feature-icon"><el-icon><Aim /></el-icon></span>
            <div>
              <strong>毫秒级动作反馈</strong>
              <span>姿态关键点实时分析，计数与标准度同步给出。</span>
            </div>
          </li>
          <li>
            <span class="feature-icon"><el-icon><MagicStick /></el-icon></span>
            <div>
              <strong>会进化的训练计划</strong>
              <span>根据疲劳、目标与历史表现动态调整下一次训练。</span>
            </div>
          </li>
          <li>
            <span class="feature-icon"><el-icon><TrendCharts /></el-icon></span>
            <div>
              <strong>看得见的成长</strong>
              <span>训练量、动作质量与连续打卡，形成你的进步曲线。</span>
            </div>
          </li>
        </ul>
      </div>

      <div class="story-footer">
        <div class="stat-chip"><strong>6</strong><span>推荐引擎</span></div>
        <div class="stat-chip"><strong>33</strong><span>姿态关键点</span></div>
        <div class="stat-chip"><strong>24/7</strong><span>AI 陪伴</span></div>
      </div>
    </aside>

    <main class="auth-main">
      <div class="auth-topbar">
        <span class="topbar-note">安全登录 · JWT 加密会话</span>
        <ThemeToggle />
      </div>

      <div class="auth-card">
        <slot />
      </div>

      <p class="auth-copyright">© {{ year }} FitVision · Move better, every rep.</p>
    </main>
  </div>
</template>

<script setup lang="ts">
import { Aim, MagicStick, TrendCharts } from '@element-plus/icons-vue'
import ThemeToggle from '../ThemeToggle.vue'

const year = new Date().getFullYear()
</script>

<style scoped>
.auth-shell {
  position: relative;
  min-height: 100vh;
  display: grid;
  grid-template-columns: minmax(0, 1.05fr) minmax(0, 0.95fr);
  overflow: hidden;
  background:
    radial-gradient(1200px 600px at 12% -10%, rgba(194, 65, 12, 0.12), transparent 55%),
    radial-gradient(900px 520px at 100% 100%, rgba(34, 211, 238, 0.14), transparent 60%),
    var(--fv-bg);
}

.auth-glow {
  position: absolute;
  border-radius: 50%;
  filter: blur(80px);
  pointer-events: none;
  opacity: 0.55;
}

.auth-glow-a {
  width: 380px;
  height: 380px;
  top: -120px;
  left: 34%;
  background: rgba(194, 65, 12, 0.28);
}

.auth-glow-b {
  width: 320px;
  height: 320px;
  bottom: -100px;
  left: -60px;
  background: rgba(34, 211, 238, 0.28);
}

.auth-story {
  position: relative;
  z-index: 1;
  display: flex;
  flex-direction: column;
  justify-content: space-between;
  padding: clamp(32px, 5vw, 64px);
  border-right: 1px solid var(--fv-border);
  background: linear-gradient(160deg, rgba(255, 255, 255, 0.55), rgba(255, 255, 255, 0.05));
  backdrop-filter: blur(6px);
}

:global(html.dark) .auth-story {
  background: linear-gradient(160deg, rgba(17, 26, 46, 0.7), rgba(7, 11, 22, 0.2));
}

.auth-brand {
  display: inline-flex;
  align-items: center;
  gap: 12px;
  color: var(--fv-text);
  text-decoration: none;
  width: fit-content;
}

.brand-mark {
  width: 42px;
  height: 42px;
  display: grid;
  place-items: center;
  border-radius: 14px;
  background: linear-gradient(135deg, var(--fv-primary), var(--fv-accent));
  color: #fff;
  font-weight: 900;
  letter-spacing: -0.5px;
  box-shadow: 0 12px 30px rgba(194, 65, 12, 0.28);
}

.brand-name {
  font-size: 20px;
  font-weight: 800;
  letter-spacing: -0.03em;
}

.story-copy {
  max-width: 520px;
  margin: 48px 0;
}

.story-eyebrow {
  display: inline-block;
  font-size: 12px;
  font-weight: 800;
  letter-spacing: 0.18em;
  color: var(--fv-primary);
  margin-bottom: 18px;
}

.story-copy h1 {
  margin: 0 0 20px;
  font-size: clamp(38px, 4.6vw, 62px);
  line-height: 1.04;
  letter-spacing: -0.045em;
  color: var(--fv-text);
  font-weight: 900;
}

.story-copy > p {
  margin: 0 0 32px;
  max-width: 440px;
  color: var(--fv-text-2);
  font-size: 16px;
  line-height: 1.75;
}

.story-features {
  list-style: none;
  margin: 0;
  padding: 0;
  display: grid;
  gap: 14px;
}

.story-features li {
  display: flex;
  gap: 14px;
  align-items: flex-start;
  padding: 14px 16px;
  border-radius: 16px;
  border: 1px solid var(--fv-border);
  background: var(--fv-surface);
  box-shadow: var(--fv-shadow-sm);
}

.feature-icon {
  flex: none;
  width: 38px;
  height: 38px;
  display: grid;
  place-items: center;
  border-radius: 12px;
  background: var(--fv-primary-soft);
  color: var(--fv-primary);
}

.story-features strong {
  display: block;
  font-size: 14px;
  color: var(--fv-text);
  margin-bottom: 2px;
}

.story-features li > div span {
  display: block;
  font-size: 12.5px;
  line-height: 1.5;
  color: var(--fv-text-2);
}

.story-footer {
  display: flex;
  gap: 10px;
  flex-wrap: wrap;
}

.stat-chip {
  display: flex;
  align-items: baseline;
  gap: 6px;
  padding: 8px 14px;
  border-radius: 999px;
  border: 1px solid var(--fv-border);
  background: var(--fv-surface);
  font-size: 12px;
  color: var(--fv-text-2);
}

.stat-chip strong {
  font-size: 16px;
  color: var(--fv-text);
}

.auth-main {
  position: relative;
  z-index: 1;
  display: flex;
  flex-direction: column;
  justify-content: center;
  align-items: center;
  padding: 32px clamp(20px, 5vw, 72px);
}

.auth-topbar {
  position: absolute;
  top: 24px;
  right: 32px;
  left: 32px;
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 16px;
}

.topbar-note {
  font-size: 12px;
  color: var(--fv-text-2);
  letter-spacing: 0.02em;
}

.auth-card {
  width: 100%;
  max-width: 430px;
  padding: clamp(26px, 4vw, 40px);
  border-radius: 26px;
  border: 1px solid var(--fv-border);
  background: var(--fv-surface);
  box-shadow: var(--fv-shadow-lg);
  animation: auth-rise 0.55s cubic-bezier(0.22, 1, 0.36, 1) both;
}

.auth-copyright {
  position: absolute;
  bottom: 22px;
  margin: 0;
  font-size: 11.5px;
  color: var(--fv-text-2);
}

@keyframes auth-rise {
  from {
    opacity: 0;
    transform: translateY(18px) scale(0.99);
  }
  to {
    opacity: 1;
    transform: translateY(0) scale(1);
  }
}

@media (max-width: 960px) {
  .auth-shell {
    grid-template-columns: 1fr;
    overflow: auto;
  }

  .auth-story {
    border-right: none;
    border-bottom: 1px solid var(--fv-border);
    padding: 28px 24px 22px;
  }

  .story-copy {
    margin: 26px 0 0;
  }

  .story-copy h1 {
    font-size: clamp(30px, 8vw, 42px);
  }

  .story-copy > p,
  .story-features,
  .story-footer {
    display: none;
  }

  .auth-main {
    padding: 72px 20px 64px;
    justify-content: flex-start;
  }

  .auth-topbar {
    top: 20px;
    left: 20px;
    right: 20px;
  }

  .topbar-note {
    display: none;
  }

  .auth-topbar {
    justify-content: flex-end;
  }

  .auth-copyright {
    position: static;
    margin-top: 28px;
    text-align: center;
  }
}
</style>
