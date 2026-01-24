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
        </div>

        <div class="controls">
            <el-button v-if="!isUpdating" type="primary" @click="startDetection" class="start-btn">
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

const videoRef = ref<HTMLVideoElement | null>(null);
const canvasRef = ref<HTMLCanvasElement | null>(null);

const props = defineProps<{
    initialExercise?: string
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

// 中文映射表 (用于显示)
const exerciseModeMap: Record<string, string> = {
    'squat': '深蹲',
    'pushup': '俯卧撑',
    'jumping_jack': '开合跳'
}

// 简单的关键词映射 (逻辑核心)
const mapExerciseToMode = (name: string) => {
    if (!name) return 'squat'
    if (name.includes('深蹲')) return 'squat'
    if (name.includes('俯卧撑')) return 'pushup'
    if (name.includes('开合跳')) return 'jumping_jack'
    return 'squat'
}

// 🔥 监听父组件传来的动作，自动切换模式
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

onMounted(() => {
    // 不默认启动
});

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
    border-radius: 8px;
    overflow: hidden;
    background: #000;
}

.canvas-wrapper {
    position: relative;
    width: 100%;
    aspect-ratio: 4/3;
}

.hidden-video {
    position: absolute;
    top: 0;
    left: 0;
    width: 100%;
    height: 100%;
    opacity: 0;
    pointer-events: none;
}

.pose-canvas {
    width: 100%;
    height: 100%;
    object-fit: contain;
}

.pose-overlay {
    position: absolute;
    top: 20px;
    left: 20px;
    right: 20px;
    display: flex;
    justify-content: space-between;
    align-items: flex-start;
    pointer-events: none;
}

.stats {
    background: rgba(0, 0, 0, 0.6);
    padding: 10px 20px;
    border-radius: 8px;
    color: white;
}

.stat-item {
    display: flex;
    flex-direction: column;
    align-items: flex-start; /* 左对齐 */
}

.stat-item .label {
    font-size: 12px;
    text-transform: uppercase;
    opacity: 0.8;
    color: #cbd5e1;
}

.stat-item .value {
    font-size: 32px;
    font-weight: bold;
    color: #4ade80; /* 绿色高亮 */
    line-height: 1;
}

.stat-item .value-sm {
    font-size: 16px;
    font-weight: bold;
    color: white;
}

.feedback {
    background: rgba(59, 130, 246, 0.9); /* 蓝色背景 */
    color: white;
    padding: 8px 16px;
    border-radius: 20px;
    font-weight: bold;
    font-size: 16px;
    box-shadow: 0 4px 6px rgba(0,0,0,0.3);
}

.loading-overlay {
    position: absolute;
    top: 0;
    left: 0;
    right: 0;
    bottom: 0;
    z-index: 10;
    display: flex;
    flex-direction: column;
    justify-content: center;
    align-items: center;
    background: rgba(0, 0, 0, 0.8);
    color: #fff;
}

.loading-text {
    margin-top: 15px;
    font-weight: 500;
}

.error-overlay {
    position: absolute;
    top: 10px;
    left: 10px;
    right: 10px;
    z-index: 20;
}

.controls {
    padding: 16px;
    text-align: center;
    background: #0f172a; /* 深色底 */
}

.start-btn {
    width: 100%;
    font-weight: bold;
    height: 40px;
}

.active-controls {
    display: flex;
    gap: 12px;
    justify-content: center;
}
</style>