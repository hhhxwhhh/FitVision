import { ref, onUnmounted } from 'vue';
import { Pose, type Results } from '@mediapipe/pose';
import { Camera } from '@mediapipe/camera_utils';
import { drawConnectors, drawLandmarks } from '@mediapipe/drawing_utils';
import { POSE_CONNECTIONS } from '@mediapipe/pose';

export function usePoseDetection() {
  const MEDIAPIPE_POSE_VERSION = '0.5.1675469404';
  const MEDIAPIPE_BASE_URL =
    (import.meta as any).env?.VITE_MEDIAPIPE_BASE ||
    `https://unpkg.com/@mediapipe/pose@${MEDIAPIPE_POSE_VERSION}`;
  const videoElement = ref<HTMLVideoElement | null>(null);
  const canvasElement = ref<HTMLCanvasElement | null>(null);
  const isUpdating = ref(false);
  const isLoaded = ref(false);
  const error = ref<string | null>(null);
  const repCount = ref(0);
  const feedback = ref('请就位');
  const exerciseMode = ref<'squat' | 'pushup' | 'jumping_jack'>('squat');
  const lastScore = ref(0);
  
  // 语音合成
  const speak = (text: string) => {
    if ('speechSynthesis' in window) {
      window.speechSynthesis.cancel(); // 取消之前的语音
      const utterance = new SpeechSynthesisUtterance(text);
      utterance.lang = 'zh-CN';
      utterance.rate = 1.2;
      window.speechSynthesis.speak(utterance);
    }
  };

  // 运动状态机
  let state: 'UP' | 'DOWN' = 'UP';
  const SQUAT_THRESHOLD_DOWN = 100;
  const SQUAT_THRESHOLD_UP = 150;
  
  const PUSHUP_THRESHOLD_DOWN = 90;
  const PUSHUP_THRESHOLD_UP = 150;

  let pose: Pose | null = null;
  let camera: Camera | null = null;

  const ensureMediaSupport = () => {
    if (!navigator?.mediaDevices?.getUserMedia) {
      throw new Error('当前浏览器不支持摄像头访问');
    }
    if (!window.isSecureContext && location.hostname !== 'localhost') {
      throw new Error('请在 HTTPS 或 localhost 环境下使用摄像头');
    }
  };

  const waitForVideoReady = (video: HTMLVideoElement, timeoutMs = 5000) => {
    return new Promise<void>((resolve, reject) => {
      if (video.readyState >= 2) {
        resolve();
        return;
      }

      let timeoutId: number | undefined;
      const onReady = () => {
        cleanup();
        resolve();
      };
      const onError = () => {
        cleanup();
        reject(new Error('摄像头视频流不可用'));
      };
      const cleanup = () => {
        video.removeEventListener('loadeddata', onReady);
        video.removeEventListener('error', onError);
        if (timeoutId) window.clearTimeout(timeoutId);
      };

      video.addEventListener('loadeddata', onReady, { once: true });
      video.addEventListener('error', onError, { once: true });
      timeoutId = window.setTimeout(() => {
        cleanup();
        reject(new Error('摄像头初始化超时'));
      }, timeoutMs);
    });
  };

  // 计算三点之间的角度
  const calculateAngle = (a: any, b: any, c: any) => {
    if (!a || !b || !c || a.visibility < 0.5 || b.visibility < 0.5 || c.visibility < 0.5) return null;
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
    if (results.image) {
      const imageWidth = (results.image as HTMLVideoElement).videoWidth || canvasElement.value.width;
      const imageHeight = (results.image as HTMLVideoElement).videoHeight || canvasElement.value.height;
      if (canvasElement.value.width !== imageWidth || canvasElement.value.height !== imageHeight) {
        canvasElement.value.width = imageWidth;
        canvasElement.value.height = imageHeight;
      }
    }

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

      if (exerciseMode.value === 'squat') {
        const hip = results.poseLandmarks[24];
        const knee = results.poseLandmarks[26];
        const ankle = results.poseLandmarks[28];

        const angle = calculateAngle(hip, knee, ankle);
        if (angle !== null) {
          if (angle < SQUAT_THRESHOLD_DOWN) {
            if (state === 'UP') {
              feedback.value = '蹲得好！';
              // 评分：蹲得越深（角度越小）分数越高，假设80度是100分
              lastScore.value = Math.min(100, Math.max(60, 100 - (angle - 80)));
            }
            state = 'DOWN';
          }
          if (angle > SQUAT_THRESHOLD_UP && state === 'DOWN') {
            state = 'UP';
            repCount.value++;
            feedback.value = `完成 ${repCount.value} 个深蹲`;
            speak(String(repCount.value));
          }
        } else {
          feedback.value = '请露出下半身';
        }
      } else if (exerciseMode.value === 'pushup') {
        const shoulder = results.poseLandmarks[12];
        const elbow = results.poseLandmarks[14];
        const wrist = results.poseLandmarks[16];

        const angle = calculateAngle(shoulder, elbow, wrist);
        if (angle !== null) {
          if (angle < PUSHUP_THRESHOLD_DOWN) {
            if (state === 'UP') {
              feedback.value = '下沉到位！';
              lastScore.value = Math.min(100, Math.max(60, 100 - (angle - 60)));
            }
            state = 'DOWN';
          }
          if (angle > PUSHUP_THRESHOLD_UP && state === 'DOWN') {
            state = 'UP';
            repCount.value++;
            feedback.value = `完成 ${repCount.value} 个俯卧撑`;
            speak(String(repCount.value));
          }
        } else {
          feedback.value = '请侧对镜头，露出手臂';
        }
      } else if (exerciseMode.value === 'jumping_jack') {
        const leftHand = results.poseLandmarks[15];
        const rightHand = results.poseLandmarks[16];
        const head = results.poseLandmarks[0];

        if (leftHand && rightHand && head) {
          const handsHigh = leftHand.y < head.y && rightHand.y < head.y;
          if (handsHigh) {
            if (state === 'UP') {
              state = 'DOWN'; // 使用 DOWN 表示跳起击掌
              lastScore.value = 100;
            }
          } else {
            if (state === 'DOWN') {
              state = 'UP';
              repCount.value++;
              feedback.value = `累计 ${repCount.value} 个开合跳`;
              speak(String(repCount.value));
            }
          }
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
      error.value = null;
      isLoaded.value = false;
      ensureMediaSupport();

      if (isUpdating.value) {
        stopPose();
      }

      pose = new Pose({
        locateFile: (file) => {
          return `${MEDIAPIPE_BASE_URL}/${file}`;
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
      await waitForVideoReady(videoElement.value);
      isUpdating.value = true;
      if (!isLoaded.value) {
        isLoaded.value = true;
      }
    } catch (err: any) {
      isUpdating.value = false;
      error.value = `MediaPipe 启动失败: ${err?.message || '未知错误'}`;
      console.error(err);
    }
  };

  const stopPose = () => {
    isUpdating.value = false;
    camera?.stop();
    pose?.close();

    if (videoElement.value?.srcObject) {
      const stream = videoElement.value.srcObject as MediaStream;
      stream.getTracks().forEach((track) => track.stop());
      videoElement.value.srcObject = null;
    }

    camera = null;
    pose = null;
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
    exerciseMode,
    lastScore,
    initPose,
    stopPose,
    resetCount
  };
}
