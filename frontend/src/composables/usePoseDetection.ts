import { ref, onUnmounted } from 'vue';
import { Pose, type PoseConfig, type Results } from '@mediapipe/pose';
import { Camera } from '@mediapipe/camera_utils';
import { drawConnectors, drawLandmarks } from '@mediapipe/drawing_utils';
import { POSE_CONNECTIONS } from '@mediapipe/pose';

export function usePoseDetection() {
  const videoElement = ref<HTMLVideoElement | null>(null);
  const canvasElement = ref<HTMLCanvasElement | null>(null);
  const isUpdating = ref(false);
  const isLoaded = ref(false);
  const error = ref<string | null>(null);
  const repCount = ref(0);
  const feedback = ref('请就位');
  
  // 运动状态机
  let state: 'UP' | 'DOWN' = 'UP';
  const SQUAT_THRESHOLD_DOWN = 100; // 蹲下的角度阈值 (小于此值认为到位)
  const SQUAT_THRESHOLD_UP = 150;   // 站起的角度阈值 (大于此值认为完成)

  let pose: Pose | null = null;
  let camera: Camera | null = null;

  // 计算三点之间的角度
  const calculateAngle = (a: any, b: any, c: any) => {
    const radians = Math.atan2(c.y - b.y, c.x - b.x) - Math.atan2(a.y - b.y, a.x - b.x);
    let angle = Math.abs(radians * 180.0 / Math.PI);
    if (angle > 180.0) angle = 360 - angle;
    return angle;
  };

  const onResults = (results: Results) => {
    if (!canvasElement.value || !videoElement.value) return;

    const canvasCtx = canvasElement.value.getContext('2d');
    if (!canvasCtx) return;

    canvasCtx.save();
    canvasCtx.clearRect(0, 0, canvasElement.value.width, canvasElement.value.height);
    
    // Draw the video frame
    canvasCtx.drawImage(
      results.image, 0, 0, canvasElement.value.width, canvasElement.value.height
    );

    // Draw Pose landmarks
    if (results.poseLandmarks) {
      drawConnectors(canvasCtx, results.poseLandmarks, POSE_CONNECTIONS,
        { color: '#00FF00', lineWidth: 4 });
      drawLandmarks(canvasCtx, results.poseLandmarks,
        { color: '#FF0000', lineWidth: 2 });

      // 深蹲逻辑处理 (使用右侧作为示例：24-26-28)
      const hip = results.poseLandmarks[24];
      const knee = results.poseLandmarks[26];
      const ankle = results.poseLandmarks[28];

      if (hip && knee && ankle) {
        const angle = calculateAngle(hip, knee, ankle);

        // 简单的逻辑判断
        if (angle < SQUAT_THRESHOLD_DOWN) {
          if (state === 'UP') {
            feedback.value = '蹲得好！继续保持';
          }
          state = 'DOWN';
        }

        if (angle > SQUAT_THRESHOLD_UP && state === 'DOWN') {
          state = 'UP';
          repCount.value++;
          feedback.value = `完成共 ${repCount.value} 个！站直`;
        }
      }
    }
    canvasCtx.restore();

    if (!isLoaded.value) {
      isLoaded.value = true;
    }
  };

  const initPose = async (video: HTMLVideoElement, canvas: HTMLCanvasElement) => {
    videoElement.value = video;
    canvasElement.value = canvas;
    repCount.value = 0; // 重置计数
    state = 'UP';
    try {
      pose = new Pose({
        locateFile: (file) => {
          return `https://cdn.jsdelivr.net/npm/@mediapipe/pose/${file}`;
        }
      });

      pose.setOptions({
        modelComplexity: 1,
        smoothLandmarks: true,
        enableSegmentation: false,
        smoothSegmentation: false,
        minDetectionConfidence: 0.5,
        minTrackingConfidence: 0.5
      });

      pose.onResults(onResults);

      camera = new Camera(videoElement.value, {
        onFrame: async () => {
          if (videoElement.value) {
            await pose?.send({ image: videoElement.value });
          }
        },
        width: 640,
        height: 480
      });

      await camera.start();
      isUpdating.value = true;
    } catch (err: any) {
      error.value = `MediaPipe 启动失败: ${err.message}`;
      console.error(err);
    }
  };

  const stopPose = () => {
    isUpdating.value = false;
    camera?.stop();
    pose?.close();
  };

  const resetCount = () => {
    repCount.value = 0;
    state = 'UP';
    feedback.value = '请就位';
  };

  onUnmounted(() => {
    stopPose();
  });

  return {
    isLoaded,
    isUpdating,
    error,
    repCount,
    feedback,
    initPose,
    stopPose,
    resetCount
  };
}
