import { ref, onUnmounted } from 'vue';
import { Pose, type Results, POSE_CONNECTIONS } from '@mediapipe/pose';
import { Camera } from '@mediapipe/camera_utils';
import { drawConnectors, drawLandmarks } from '@mediapipe/drawing_utils';
import { calculateAngle, OneEuroFilter, normalizeLandmarks, matchPoseSignature } from '@/utils/poseMatching';

export function usePoseDetection() {
  const MEDIAPIPE_POSE_VERSION = '0.5.1675469404';
  const MEDIAPIPE_BASE_URL =
    (import.meta as any).env?.VITE_MEDIAPIPE_BASE ||
    `https://cdn.jsdelivr.net/npm/@mediapipe/pose@${MEDIAPIPE_POSE_VERSION}`;
  
  const getMediaPipeAssetUrl = (file: string) => {
    const normalizedBase = MEDIAPIPE_BASE_URL.replace(/\/+$/, '');
    const normalizedFile = file.replace(/^\/+/, '');
    return `${normalizedBase}/${normalizedFile}`;
  };

  // 补丁：关键点。解决 MediaPipe 在 Web / Vite 环境下特定的 Aborted(Module.arguments) 报错
  if (typeof window !== 'undefined' && !(window as any).arguments) {
    (window as any).arguments = [];
  }

  const videoElement = ref<HTMLVideoElement | null>(null);
  const canvasElement = ref<HTMLCanvasElement | null>(null);
  const isUpdating = ref(false);
  const isLoaded = ref(false);
  const error = ref<string | null>(null);
  
  const repCount = ref(0);
  const feedback = ref('请就位');
  const repProgress = ref(0); 
  const exerciseMode = ref<'squat' | 'pushup' | 'jumping_jack' | 'plank'>('squat');
  const lastScore = ref(0);
  const duration = ref(0); // 持续时间，用于平板支撑等

  // 1. 坐标平滑滤波器组 (为 33 个关键点的 X, Y, Z 分别创建滤波器)
  const landmarkFilters = Array.from({ length: 33 }, () => ({
    x: new OneEuroFilter(1.0, 0.05),
    y: new OneEuroFilter(1.0, 0.05),
    z: new OneEuroFilter(1.0, 0.05)
  }));
  const angleFilter = new OneEuroFilter(1.5, 0.1);
  const progressFilter = new OneEuroFilter(0.5, 0.0);

  let state: 'UP' | 'DOWN' = 'UP';
  let lastStateChange = Date.now();
  let coachTimer: number | null = null;
  let plankStartTime: number | null = null;
  let pose: Pose | null = null;
  let camera: Camera | null = null;

  const speak = (text: string) => {
    if ('speechSynthesis' in window) {
      window.speechSynthesis.cancel();
      const utterance = new SpeechSynthesisUtterance(text);
      utterance.lang = 'zh-CN';
      utterance.rate = 1.3;
      window.speechSynthesis.speak(utterance);
    }
  };

  const clearCoachTimer = () => {
    if (coachTimer) {
      window.clearInterval(coachTimer);
      coachTimer = null;
    }
  };

  const startCoachTimer = () => {
    clearCoachTimer();
    coachTimer = window.setInterval(() => {
      const idleTime = Date.now() - lastStateChange;
      if (idleTime > 8000 && isUpdating.value) {
        speak(state === 'UP' ? '加油，动作快一点！' : '坚持住，慢慢起来！');
        lastStateChange = Date.now();
      }
    }, 1000);
  };

  const onResults = (results: Results) => {
    if (!canvasElement.value || !videoElement.value) return;
    const canvasCtx = canvasElement.value.getContext('2d');
    if (!canvasCtx) return;

    canvasCtx.save();
    canvasCtx.clearRect(0, 0, canvasElement.value.width, canvasElement.value.height);
    canvasCtx.drawImage(results.image, 0, 0, canvasElement.value.width, canvasElement.value.height);

    if (results.poseLandmarks) {
      const now = Date.now();
      
      // 1. 坐标级平滑 (Coordinate-level Smoothing)
      // 这里的优化点在于对每个关节的三维坐标进行物理级滤波，使得骨骼渲染极其稳定
      const smoothedLandmarks = results.poseLandmarks.map((lm, i) => {
        if (i >= 33) return lm;
        return {
          ...lm,
          x: landmarkFilters[i].x.filter(lm.x, now),
          y: landmarkFilters[i].y.filter(lm.y, now),
          z: landmarkFilters[i].z.filter(lm.z, now),
        };
      });

      // 2. 动态着色渲染：根据最后一次动作得分改变骨骼颜色
      const skeletonColor = lastScore.value > 88 ? 'rgba(0, 255, 100, 0.6)' : 'rgba(255, 165, 0, 0.6)';
      drawConnectors(canvasCtx, smoothedLandmarks, POSE_CONNECTIONS, { color: skeletonColor, lineWidth: 5 });
      drawLandmarks(canvasCtx, smoothedLandmarks, { 
        color: '#FFFFFF', 
        lineWidth: 1, 
        radius: (data: any) => (data.index > 10 ? 3 : 1) 
      });

      // 3. 增强版运动学判定逻辑 (Kinematics with Signature Matching)
      if (exerciseMode.value === 'squat') {
        const angle = calculateAngle(smoothedLandmarks[24], smoothedLandmarks[26], smoothedLandmarks[28]);
        if (angle) {
          const smoothedAngle = angleFilter.filter(angle, now);
          repProgress.value = Math.floor(progressFilter.filter(Math.max(0, Math.min(100, (170 - smoothedAngle) / 80 * 100)), now));

          if (smoothedAngle < 105 && state === 'UP') {
            state = 'DOWN';
            feedback.value = '下沉到位！';
            lastStateChange = now;
            
            // 使用 SOTA 签名匹配进行实时打分 (Signature Match)
            const signatureScore = matchPoseSignature(smoothedLandmarks, 'squat_down');
            lastScore.value = Math.round(signatureScore * 100);
          } else if (smoothedAngle > 155 && state === 'DOWN') {
            state = 'UP';
            repCount.value++;
            speak(String(repCount.value));
            feedback.value = lastScore.value > 90 ? '完美动作！' : '保持呼吸';
            lastStateChange = now;
          }
        }
      } else if (exerciseMode.value === 'pushup') {
          const angle = calculateAngle(smoothedLandmarks[12], smoothedLandmarks[14], smoothedLandmarks[16]);
          if (angle) {
            const smoothed = angleFilter.filter(angle, now);
            repProgress.value = Math.floor(progressFilter.filter(Math.max(0, Math.min(100, (160 - smoothed) / 85 * 100)), now));
            
            if (smoothed < 95 && state === 'UP') {
                state = 'DOWN';
                feedback.value = '准备撑起！';
                lastStateChange = now;
                const signatureScore = matchPoseSignature(smoothedLandmarks, 'pushup_down');
                lastScore.value = Math.round(signatureScore * 100);
            } else if (smoothed > 150 && state === 'DOWN') {
                state = 'UP';
                repCount.value++;
                speak(String(repCount.value));
                lastStateChange = now;
            }
          }
      } else if (exerciseMode.value === 'plank') {
          // 平板支撑：利用 Signature 评估姿态稳定性与准确度 (SOTA Approach)
          const signatureScore = matchPoseSignature(smoothedLandmarks, 'plank');
          lastScore.value = Math.round(signatureScore * 100);
          
          if (lastScore.value > 85) {
              if (!plankStartTime) plankStartTime = now;
              duration.value = Math.floor((now - plankStartTime) / 1000);
              feedback.value = `坚持住！稳定性: ${lastScore.value}%`;
              repProgress.value = 100;
          } else {
              plankStartTime = null;
              feedback.value = '⚠️ 请保持身体平直';
              repProgress.value = lastScore.value;
          }
      } else if (exerciseMode.value === 'jumping_jack') {
          const score = matchPoseSignature(smoothedLandmarks, 'jumping_jack_up');
          // 开合跳：手部超过头部的同时也检查整体签名
          const avgHandY = (smoothedLandmarks[15].y + smoothedLandmarks[16].y) / 2;
          const headY = smoothedLandmarks[0].y;
          
          if (avgHandY < headY && score > 0.7 && state === 'UP') {
              state = 'DOWN';
              lastStateChange = now;
              lastScore.value = Math.round(score * 100);
          } else if (avgHandY > headY + 0.2 && state === 'DOWN') {
              state = 'UP';
              repCount.value++;
              speak(String(repCount.value));
              feedback.value = lastScore.value > 85 ? '漂亮！' : '动作幅度再大点';
              lastStateChange = now;
          }
      }
    }
    canvasCtx.restore();

    if (!isLoaded.value) {
      isLoaded.value = true;
      startCoachTimer();
    }
  };

  const initPose = async (video: HTMLVideoElement, canvas: HTMLCanvasElement) => {
    videoElement.value = video;
    canvasElement.value = canvas;
    error.value = null;
    isLoaded.value = false;
    
    try {
      pose = new Pose({ locateFile: (file) => getMediaPipeAssetUrl(file) });
      pose.setOptions({
        modelComplexity: 1,
        smoothLandmarks: true,
        minDetectionConfidence: 0.5,
        minTrackingConfidence: 0.5
      });
      pose.onResults(onResults);

      camera = new Camera(video, {
        onFrame: async () => {
          if (isUpdating.value) await pose?.send({ image: video });
        },
        width: 1280, // 高清模式提升识别精度
        height: 720
      });
      
      await camera.start();
      isUpdating.value = true;
    } catch (err: any) {
      error.value = `启动失败: ${err.message}`;
      console.error(err);
    }
  };

  const stopPose = () => {
    isUpdating.value = false;
    clearCoachTimer();
    camera?.stop();
    pose?.close();
    camera = null;
    pose = null;
  };

  onUnmounted(stopPose);

  return {
    isLoaded,
    isUpdating,
    error,
    repCount,
    feedback,
    repProgress,
    exerciseMode,
    lastScore,
    duration,
    initPose,
    stopPose,
    resetCount: () => {
      repCount.value = 0;
      duration.value = 0;
      plankStartTime = null;
      state = 'UP';
      feedback.value = '请就位';
    }
  };
}
