<template>
  <div class="pose-preview-container">
    <div v-if="error" class="error-overlay">
      <el-alert :title="error" type="error" show-icon />
    </div>

    <div v-if="!isLoaded && isUpdating" class="loading-overlay">
      <el-skeleton animated>
        <template #template>
          <el-skeleton-item variant="rect" style="width: 100%; height: 480px" />
        </template>
      </el-skeleton>
      <div class="loading-text">AI 模型加载中...</div>
    </div>

    <div class="canvas-wrapper">
      <video ref="videoRef" class="hidden-video" autoplay muted playsinline></video>
      <canvas ref="canvasRef" width="640" height="480" class="pose-canvas"></canvas>

      <div v-if="isUpdating" class="pose-overlay">
        <div class="stats">
          <div class="stat-item">
            <span class="label">当前动作</span>
            <span class="value-sm">{{ exerciseModeMap[exerciseMode] }}</span>
          </div>
          <div class="stat-item" style="margin-top: 10px;">
            <span class="label">计数</span>
            <span class="value">{{ repCount }}</span>
          </div>
        </div>
        <div class="feedback">{{ feedback }}</div>
      </div>

      <div v-if="!isUpdating" class="standby-overlay">
        <div v-if="demoGif" class="image-container">
          <img :src="demoGif" class="cover-image" alt="动作示范" />
          <div class="image-backdrop"></div>
          <div class="demo-badge">
            <el-icon><VideoPlay /></el-icon> 标准示范
          </div>
        </div>
        
        <div v-else class="placeholder-container">
          <el-icon :size="80" color="#475569"><VideoCamera /></el-icon>
          <p>等待开启摄像头</p>
        </div>

        <div class="center-action">
          <el-button type="primary" size="large" circle class="big-play-btn" @click="startDetection">
            <el-icon :size="36"><CaretRight /></el-icon>
          </el-button>
          <div class="action-text">点击开始 {{ exerciseModeMap[exerciseMode] || '训练' }}</div>
        </div>
      </div>
    </div>

    <div class="controls">
      <el-button v-if="!isUpdating" type="primary" plain @click="startDetection" class="start-btn-mini">
        开启摄像头 AI
      </el-button>
      
      <div v-else class="active-controls">
        <el-button type="danger" @click="stopDetection">关闭摄像头</el-button>
        <el-button type="warning" @click="resetCount">重新计数</el-button>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted, watch } from 'vue';
import { usePoseDetection } from '../../composables/usePoseDetection';
import { VideoCamera, CaretRight, VideoPlay } from '@element-plus/icons-vue'; // 引入图标

const videoRef = ref<HTMLVideoElement | null>(null);
const canvasRef = ref<HTMLCanvasElement | null>(null);

// 🔥 核心修改：接收 demoGif 参数
const props = defineProps<{
  initialExercise?: string,
  demoGif?: string  
}>();

const {
  isLoaded,
  isUpdating,
  error,
  repCount,
  feedback,
  exerciseMode,
  lastScore,
  initPose,
  stopPose,
  resetCount
} = usePoseDetection();

// 中文映射表
const exerciseModeMap: Record<string, string> = {
  'squat': '深蹲',
  'pushup': '俯卧撑',
  'jumping_jack': '开合跳',
  'lunge': '弓步蹲',
  'plank': '平板支撑'
}

// 关键词映射逻辑
const mapExerciseToMode = (name: string) => {
  if (!name) return 'squat'
  if (name.includes('深蹲')) return 'squat'
  if (name.includes('俯卧撑')) return 'pushup'
  if (name.includes('开合跳')) return 'jumping_jack'
  // 默认 fallback
  return 'squat'
}

// 监听动作变化
watch(() => props.initialExercise, (newVal) => {
  if (newVal) {
    exerciseMode.value = mapExerciseToMode(newVal)
    resetCount()
  }
}, { immediate: true });

const emit = defineEmits(['update:reps', 'update:score']);

watch(repCount, (newVal) => {
  emit('update:reps', newVal);
});

watch(lastScore, (newVal) => {
  emit('update:score', newVal);
});

const startDetection = async () => {
  if (videoRef.value && canvasRef.value) {
    await initPose(videoRef.value, canvasRef.value);
  }
};

const stopDetection = () => {
  stopPose();
};

defineExpose({
  startDetection,
  stopDetection,
  resetCount
});
</script>

<style scoped>
.pose-preview-container {
  position: relative;
  width: 100%;
  max-width: 640px;
  margin: 0 auto;
  border-radius: 12px;
  overflow: hidden;
  background: #0f172a;
  border: 1px solid #1e293b;
}

.canvas-wrapper {
  position: relative;
  width: 100%;
  aspect-ratio: 4/3;
  background: #000;
}

.hidden-video {
  position: absolute;
  top: 0; left: 0; width: 100%; height: 100%;
  opacity: 0; pointer-events: none;
}

.pose-canvas {
  width: 100%; height: 100%; object-fit: contain;
}

/* --- 遮罩样式 --- */
.standby-overlay {
  position: absolute;
  top: 0; left: 0; width: 100%; height: 100%;
  display: flex;
  flex-direction: column;
  justify-content: center;
  align-items: center;
  z-index: 5;
  overflow: hidden;
}

.image-container {
  position: absolute;
  width: 100%; height: 100%;
  top: 0; left: 0;
}

.cover-image {
  width: 100%; height: 100%;
  object-fit: cover; /* 铺满 */
  opacity: 0.5; /* 变暗 */
}

.image-backdrop {
  position: absolute;
  top: 0; left: 0; width: 100%; height: 100%;
  background: radial-gradient(circle, rgba(15,23,42,0.3) 0%, rgba(15,23,42,0.8) 100%);
}

.demo-badge {
  position: absolute;
  top: 16px; left: 16px;
  background: rgba(0, 0, 0, 0.6);
  color: #e2e8f0;
  padding: 4px 12px;
  border-radius: 20px;
  font-size: 12px;
  display: flex;
  align-items: center;
  gap: 6px;
  backdrop-filter: blur(4px);
}

.placeholder-container {
  display: flex;
  flex-direction: column;
  align-items: center;
  color: #64748b;
}

.center-action {
  position: relative;
  z-index: 10;
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 16px;
}

.big-play-btn {
  width: 80px; height: 80px;
  font-size: 36px;
  border: 4px solid rgba(255, 255, 255, 0.2);
  background: rgba(16, 185, 129, 0.9); /* 绿色主色调 */
  color: white;
  box-shadow: 0 0 0 0 rgba(16, 185, 129, 0.7);
  animation: pulse-green 2s infinite;
  transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1);
}

.big-play-btn:hover {
  transform: scale(1.1);
  background: #10b981;
}

.action-text {
  color: white;
  font-size: 16px;
  font-weight: 600;
  text-shadow: 0 2px 4px rgba(0,0,0,0.8);
  letter-spacing: 1px;
}

/* --- 运行时样式 --- */
.pose-overlay {
  position: absolute;
  top: 16px; left: 16px; right: 16px;
  display: flex;
  justify-content: space-between;
  pointer-events: none;
}

.stats {
  background: rgba(15, 23, 42, 0.8);
  padding: 12px 20px;
  border-radius: 12px;
  border: 1px solid rgba(255, 255, 255, 0.1);
  backdrop-filter: blur(4px);
}

.stat-item {
  display: flex; flex-direction: column; align-items: flex-start;
}

.stat-item .label {
  font-size: 11px; text-transform: uppercase; color: #94a3b8; margin-bottom: 2px;
}

.stat-item .value {
  font-size: 28px; font-weight: 800; color: #4ade80; line-height: 1;
}

.stat-item .value-sm {
  font-size: 15px; font-weight: 700; color: white;
}

.feedback {
  background: rgba(59, 130, 246, 0.9);
  color: white;
  padding: 8px 16px;
  border-radius: 20px;
  font-weight: 600;
  font-size: 14px;
  box-shadow: 0 4px 12px rgba(59, 130, 246, 0.3);
}

/* --- 底部控制 --- */
.controls {
  padding: 16px;
  background: #0f172a;
  border-top: 1px solid #1e293b;
  display: flex;
  justify-content: center;
}

.active-controls {
  display: flex; gap: 12px;
}

.loading-overlay {
  position: absolute; top: 0; left: 0; width: 100%; height: 100%;
  z-index: 20; background: rgba(0,0,0,0.8);
  display: flex; flex-direction: column; justify-content: center; align-items: center; color: white;
}

@keyframes pulse-green {
  0% { box-shadow: 0 0 0 0 rgba(16, 185, 129, 0.7); }
  70% { box-shadow: 0 0 0 15px rgba(16, 185, 129, 0); }
  100% { box-shadow: 0 0 0 0 rgba(16, 185, 129, 0); }
}
</style>