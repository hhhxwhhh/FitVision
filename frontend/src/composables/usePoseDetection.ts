import { ref, onUnmounted } from 'vue';
import { Pose, type Results, POSE_CONNECTIONS } from '@mediapipe/pose';
import { Camera } from '@mediapipe/camera_utils';
import { drawConnectors, drawLandmarks } from '@mediapipe/drawing_utils';
import { calculateAngle, OneEuroFilter, normalizeLandmarks, matchPoseSignature } from '../utils/poseMatching';
import apiClient from '../api';

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
  const isAnalyzingVlm = ref(false);
  const vlmAdvice = ref('');
  const diagnosisReport = ref<any>(null);
  const latestLandmarks = ref<any[] | null>(null);
  let lastVlmCallTime = 0; // VLM 自动触发的时间戳
  const VLM_AUTO_THRESHOLD = 60; // 自动触发的分数阈值
  const VLM_COOLDOWN = 25000; // 25秒冷却时间，防止频繁开销

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
      const smoothedLandmarks = results.poseLandmarks.map((lm, i) => {
        if (i >= 33 || !landmarkFilters[i]) return lm;
        return {
          ...lm,
          x: landmarkFilters[i].x.filter(lm.x, now),
          y: landmarkFilters[i].y.filter(lm.y, now),
          z: landmarkFilters[i].z.filter(lm.z, now),
        };
      });
      latestLandmarks.value = smoothedLandmarks;

      // 2. 姿态归一化 (Skeletal Normalization)
      const normalizedLandmarks = normalizeLandmarks(smoothedLandmarks as any);

      // 3. 实时绘制与运动学分析
      const skeletonColor = lastScore.value > 88 ? 'rgba(0, 255, 100, 0.6)' : 'rgba(255, 165, 0, 0.6)';
      drawConnectors(canvasCtx, smoothedLandmarks, POSE_CONNECTIONS, { color: skeletonColor, lineWidth: 5 });
      drawLandmarks(canvasCtx, smoothedLandmarks, { color: '#FFFFFF', radius: 2 });

      if (exerciseMode.value === 'squat') {
        const p1 = smoothedLandmarks[24], p2 = smoothedLandmarks[26], p3 = smoothedLandmarks[28];
        if (p1 && p2 && p3) {
          const angle = calculateAngle(p1, p2, p3);
          if (angle !== null) {
            const smoothed = angleFilter.filter(angle, now);
            repProgress.value = Math.floor(progressFilter.filter(Math.max(0, Math.min(100, (170 - smoothed) / 80 * 100)), now));
            if (smoothed < 105 && state === 'UP') {
              state = 'DOWN';
              feedback.value = '下沉到位！';
              lastStateChange = now;
              const sig = matchPoseSignature(normalizedLandmarks as any, 'squat_down');
              lastScore.value = Math.round(sig * 100);
            } else if (smoothed > 155 && state === 'DOWN') {
              state = 'UP';
              repCount.value++;
              speak(String(repCount.value));
              feedback.value = lastScore.value > 90 ? '完美动作！' : '保持呼吸';
              lastStateChange = now;
            }
          }
        }
      } else if (exerciseMode.value === 'pushup') {
        const p1 = smoothedLandmarks[12], p2 = smoothedLandmarks[14], p3 = smoothedLandmarks[16];
        if (p1 && p2 && p3) {
          const angle = calculateAngle(p1, p2, p3);
          if (angle !== null) {
            const smoothed = angleFilter.filter(angle, now);
            repProgress.value = Math.floor(progressFilter.filter(Math.max(0, Math.min(100, (160 - smoothed) / 85 * 100)), now));
            if (smoothed < 95 && state === 'UP') {
              state = 'DOWN';
              feedback.value = '准备撑起！';
              lastStateChange = now;
              const sig = matchPoseSignature(normalizedLandmarks as any, 'pushup_down');
              lastScore.value = Math.round(sig * 100);
            } else if (smoothed > 150 && state === 'DOWN') {
              state = 'UP';
              repCount.value++;
              speak(String(repCount.value));
              lastStateChange = now;
            }
          }
        }
      } else if (exerciseMode.value === 'plank') {
        const sig = matchPoseSignature(normalizedLandmarks as any, 'plank');
        lastScore.value = Math.round(sig * 100);
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
        const p1 = smoothedLandmarks[15], p2 = smoothedLandmarks[16], p3 = smoothedLandmarks[0];
        const sig = matchPoseSignature(normalizedLandmarks as any, 'jumping_jack_up');
        if (p1 && p2 && p3) {
          const avgY = (p1.y + p2.y) / 2;
          if (avgY < p3.y && sig > 0.7 && state === 'UP') {
            state = 'DOWN';
            lastStateChange = now;
            lastScore.value = Math.round(sig * 100);
          } else if (avgY > p3.y + 0.2 && state === 'DOWN') {
            state = 'UP';
            repCount.value++;
            speak(String(repCount.value));
            feedback.value = lastScore.value > 85 ? '漂亮！' : '幅度再大点';
            lastStateChange = now;
          }
        }
      }
    }

    // 🔥 VLM 智能自动纠错机制
    const currentTime = Date.now();
    if (isUpdating.value && !isAnalyzingVlm.value && lastScore.value > 0 && lastScore.value < VLM_AUTO_THRESHOLD) {
      if (currentTime - lastVlmCallTime > VLM_COOLDOWN) {
        lastVlmCallTime = currentTime;
        analyzeWithVisionModel();
      }
    }
    
    canvasCtx.restore();

    if (!isLoaded.value) {
      isLoaded.value = true;
      startCoachTimer();
    }
  };

  const captureFrameBase64 = (): string | null => {
    if (!videoElement.value) return null;
    const tempCanvas = document.createElement('canvas');
    tempCanvas.width = videoElement.value.videoWidth || 640;
    tempCanvas.height = videoElement.value.videoHeight || 480;
    const tempCtx = tempCanvas.getContext('2d');
    if (!tempCtx) return null;
    tempCtx.drawImage(videoElement.value, 0, 0, tempCanvas.width, tempCanvas.height);
    return tempCanvas.toDataURL('image/jpeg', 0.85);
  };

  const analyzeWithVisionModel = async (mode: 'realtime' | 'diagnosis' = 'realtime') => {
    if (!isUpdating.value) {
      feedback.value = '请先开启摄像头';
      return;
    }
    const image = captureFrameBase64();
    if (!image || !latestLandmarks.value) {
      feedback.value = '画面或关键点未准备好，请稍后重试';
      return;
    }

    isAnalyzingVlm.value = true;
    try {
      const response = await apiClient.post('/ai/vlm-analysis/', {
        image_base64: image,
        mode: mode,
        exercise_type: exerciseMode.value,
        landmarks: latestLandmarks.value,
        motion_metrics: {
          rep_progress: repProgress.value,
          last_score: lastScore.value,
          rep_count: repCount.value,
        },
      });

      if (mode === 'diagnosis') {
        diagnosisReport.value = response.data;
        feedback.value = `✅ 诊断报告已生成: ${response.data.summary}`;
        speak("动作分析报告已准备就绪，请在侧边栏查看详细建议。");
      } else {
        // 实时纠错模式数据处理
        const { advice, tts_alert, safety_risks, score_vlm } = response.data;
        
        vlmAdvice.value = advice || '分析完成';
        
        if (safety_risks) {
          feedback.value = `🛑 警告: ${safety_risks}`;
        } else {
          feedback.value = `🤖 ${advice}`;
        }

        if (score_vlm) {
          lastScore.value = Math.round(Number(score_vlm));
        }

        if (tts_alert) {
          speak(tts_alert);
        } else if (advice) {
          speak(advice.substring(0, 30));
        }
      }
    } catch (err: any) {
      const message = err?.response?.data?.detail || '视觉大模型分析失败，请稍后重试';
      feedback.value = `⚠️ ${message}`;
    } finally {
      isAnalyzingVlm.value = false;
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
    isAnalyzingVlm,
    vlmAdvice,
    diagnosisReport,
    initPose,
    analyzeWithVisionModel,
    stopPose,
    resetCount: () => {
      repCount.value = 0;
      duration.value = 0;
      plankStartTime = null;
      state = 'UP';
      feedback.value = '请就位';
      vlmAdvice.value = '';
    }
  };
}
