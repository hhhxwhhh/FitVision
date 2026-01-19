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
            <video ref="videoRef" class="hidden-video" playsinline></video>
            <canvas ref="canvasRef" width="640" height="480" class="pose-canvas"></canvas>

            <div v-if="isUpdating" class="pose-overlay">
                <div class="stats">
                    <div class="stat-item">
                        <span class="label">计数</span>
                        <span class="value">{{ repCount }}</span>
                    </div>
                </div>
                <div class="feedback">{{ feedback }}</div>
            </div>
        </div>

        <div class="controls">
            <el-button v-if="!isUpdating" type="primary" @click="startDetection">开启摄像头 AI</el-button>
            <template v-else>
                <el-button type="danger" @click="stopDetection">关闭摄像头</el-button>
                <el-button type="warning" @click="resetCount">重新计数</el-button>
            </template>
        </div>
    </div>
</template>

<script setup lang="ts">
import { ref, onMounted } from 'vue';
import { usePoseDetection } from '../../composables/usePoseDetection';

const videoRef = ref<HTMLVideoElement | null>(null);
const canvasRef = ref<HTMLCanvasElement | null>(null);

const {
    isLoaded,
    isUpdating,
    error,
    repCount,
    feedback,
    initPose,
    stopPose,
    resetCount

watch(repCount, (newVal) => {
    emit('update:reps', newVal);
});

defineExpose({
    resetCount
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
    // 不默认启动，让用户手动点，或者根据需求自动启
});

defineExpose({
    startDetection,
    stopDetection
})
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
    display: none;
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
    align-items: center;
}

.stat-item .label {
    font-size: 12px;
    text-transform: uppercase;
    opacity: 0.8;
}

.stat-item .value {
    font-size: 32px;
    font-weight: bold;
    color: #409EFF;
}

.feedback {
    background: rgba(64, 158, 255, 0.8);
    color: white;
    padding: 8px 16px;
    border-radius: 20px;
    font-weight: bold;
    font-size: 16px;
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
    background: rgba(0, 0, 0, 0.7);
    color: #fff;
}

.loading-text {
    margin-top: 15px;
}

.error-overlay {
    position: absolute;
    top: 10px;
    left: 10px;
    right: 10px;
    z-index: 20;
}

.controls {
    padding: 10px;
    text-align: center;
    background: #1a1a1a;
}
</style>
