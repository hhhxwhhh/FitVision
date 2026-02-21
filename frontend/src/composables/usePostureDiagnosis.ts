import { ref, onUnmounted } from 'vue';
import { Pose, type Results, POSE_CONNECTIONS } from '@mediapipe/pose';
import { Camera } from '@mediapipe/camera_utils';
import { drawConnectors, drawLandmarks } from '@mediapipe/drawing_utils';
import { OneEuroFilter, normalizeLandmarks } from '@/utils/poseMatching';
import apiClient from '@/api';

export interface PostureReport {
  score: number;
  summary: string;
  body_alignment?: string;
  risk_level?: 'low' | 'medium' | 'high';
  improvement_plan?: string;
  scenario_application?: string;
  system_recommendations?: { id: number; name: string; muscle: string }[];
  details: {
    label: string;
    value: string;
    status: 'normal' | 'warning' | 'danger';
    advice: string;
  }[];
}

export function usePostureDiagnosis() {
  const MEDIAPIPE_POSE_VERSION = '0.5.1675469404';
  const MEDIAPIPE_BASE_URL = `https://cdn.jsdelivr.net/npm/@mediapipe/pose@${MEDIAPIPE_POSE_VERSION}`;

  const videoElement = ref<HTMLVideoElement | null>(null);
  const canvasElement = ref<HTMLCanvasElement | null>(null);
  const isLoaded = ref(false);
  const isAnalyzing = ref(false);
  const currentMode = ref<'front' | 'side'>('front');
  const lastResults = ref<Results | null>(null);
  const report = ref<PostureReport | null>(null);

  // 补丁：解决 MediaPipe 在某些环境下的 Aborted(Module.arguments) 报错
  if (typeof window !== 'undefined' && !(window as any).arguments) {
    (window as any).arguments = [];
  }

  // 1. 增加滤波器以获得平滑的分析基准
  const landmarkFilters = Array.from({ length: 33 }, () => ({
    x: new OneEuroFilter(1.0, 0.05),
    y: new OneEuroFilter(1.0, 0.05),
    z: new OneEuroFilter(1.0, 0.05)
  }));

  let pose: Pose | null = null;
  let camera: Camera | null = null;

  const initPose = async () => {
    pose = new Pose({
      locateFile: (file) => `${MEDIAPIPE_BASE_URL}/${file}`,
    });

    pose.setOptions({
      modelComplexity: 1,
      smoothLandmarks: true,
      minDetectionConfidence: 0.5,
      minTrackingConfidence: 0.5,
    });

    pose.onResults((results) => {
      lastResults.value = results;
      drawFrame(results);
    });

    if (videoElement.value) {
      camera = new Camera(videoElement.value, {
        onFrame: async () => {
          if (pose && videoElement.value) {
            await pose.send({ image: videoElement.value });
          }
        },
        width: 1280,
        height: 720,
      });
      await camera.start();
      isLoaded.value = true;
    }
  };

  const drawFrame = (results: Results) => {
    if (!canvasElement.value) return;
    const ctx = canvasElement.value.getContext('2d');
    if (!ctx) return;

    ctx.save();
    ctx.clearRect(0, 0, canvasElement.value.width, canvasElement.value.height);
    ctx.drawImage(results.image, 0, 0, canvasElement.value.width, canvasElement.value.height);

    if (results.poseLandmarks) {
      const now = Date.now();
      const smoothed = results.poseLandmarks.map((lm, i) => ({
        ...lm,
        x: landmarkFilters[i].x.filter(lm.x, now),
        y: landmarkFilters[i].y.filter(lm.y, now)
      }));

      // 绘制诊断辅助线 (Frontal lines)
      if (currentMode.value === 'front') {
         ctx.strokeStyle = 'rgba(255, 255, 255, 0.3)';
         ctx.lineWidth = 1;
         // 肩平线
         const sY = (smoothed[11].y + smoothed[12].y) / 2 * canvasElement.value.height;
         ctx.beginPath(); ctx.moveTo(0, sY); ctx.lineTo(canvasElement.value.width, sY); ctx.stroke();
         // 髋平线
         const hY = (smoothed[23].y + smoothed[24].y) / 2 * canvasElement.value.height;
         ctx.beginPath(); ctx.moveTo(0, hY); ctx.lineTo(canvasElement.value.width, hY); ctx.stroke();
      }

      drawConnectors(ctx, smoothed, POSE_CONNECTIONS, { color: '#10b981', lineWidth: 4 });
      drawLandmarks(ctx, smoothed, { color: '#FFFFFF', lineWidth: 1, radius: 2 });
    }
    ctx.restore();
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

  const analyze = async () => {
    if (!lastResults.value?.poseLandmarks) return;
    isAnalyzing.value = true;
    
    // 1. 获取画面快照
    const image = captureFrameBase64();
    
    // 2. 基础规则预分析
    const landmarks = normalizeLandmarks(lastResults.value.poseLandmarks as any);
    const localDetails: PostureReport['details'] = [];
    let baseScore = 100;

    if (currentMode.value === 'front') {
        const shDiff = Math.abs(landmarks[11].y - landmarks[12].y);
        if (shDiff > 0.08) {
            baseScore -= 20;
            localDetails.push({ label: '肩膀对称度', value: 'Danger', status: 'danger', advice: '存在明显高低肩，VLM 将深度评估脊柱风险。' });
        }
    }

    try {
        // 3. 调用核心 VLM 诊断引擎
        const response = await apiClient.post('/ai/vlm-analysis/', {
            image_base64: image,
            mode: 'diagnosis',
            exercise_type: currentMode.value === 'front' ? '正面全景体能' : '侧方视角体态',
            landmarks: lastResults.value.poseLandmarks,
            motion_metrics: { last_score: baseScore }
        });

        const vlmData = response.data;
        
        // 4. 合并报告
        report.value = {
            score: vlmData.score || baseScore,
            summary: vlmData.summary || '诊断完成',
            body_alignment: vlmData.body_alignment,
            risk_level: vlmData.risk_level,
            improvement_plan: vlmData.improvement_plan,
            scenario_application: vlmData.scenario_application,
            system_recommendations: vlmData.system_recommendations,
            details: localDetails.length ? localDetails : [
                { label: '初步扫描', value: 'Normal', status: 'normal', advice: '正在生成深度视觉建议...' }
            ]
        };

        // 5. 持久化到后端
        await apiClient.post('/ai/posture-diagnosis/', {
            diagnosis_type: currentMode.value,
            score: report.value.score,
            summary: report.value.summary,
            detailed_report: vlmData,
            landmarks_data: lastResults.value.poseLandmarks
        });

    } catch (err) {
        console.error('VLM Diagnosis Integration Error:', err);
        // 回退逻辑
        report.value = {
            score: baseScore,
            summary: '本地扫描快查',
            details: localDetails
        };
    } finally {
        isAnalyzing.value = false;
    }
  };

  const stop = () => {
    isAnalyzing.value = false;
    camera?.stop();
    pose?.close();
  };

  return {
    videoElement,
    canvasElement,
    isLoaded,
    isAnalyzing,
    currentMode,
    report,
    initPose,
    analyze,
    stop
  };
}
