import { ref, onUnmounted } from 'vue';
import { Pose, type Results, POSE_CONNECTIONS } from '@mediapipe/pose';
import { Camera } from '@mediapipe/camera_utils';
import { drawConnectors, drawLandmarks } from '@mediapipe/drawing_utils';
import { OneEuroFilter, normalizeLandmarks } from '@/utils/poseMatching';
import apiClient from '@/api';

export interface PostureReport {
  score: number;
  summary: string;
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

  const analyze = async () => {
    if (!lastResults.value?.poseLandmarks) return;
    isAnalyzing.value = true;
    
    // 2. 使用归一化数据以脱离距离限制
    const landmarks = normalizeLandmarks(lastResults.value.poseLandmarks as any);
    const newReport: PostureReport = {
      score: 100,
      summary: '姿态良好',
      details: []
    };

    if (currentMode.value === 'front') {
      // 1. 肩膀对称性
      const shDiff = Math.abs(landmarks[11].y - landmarks[12].y);
      if (shDiff > 0.08) {
        newReport.score -= 20;
        newReport.details.push({ label: '显著高低肩', value: 'Danger', status: 'danger', advice: '建议咨询物理治疗师检查脊柱侧弯。' });
      } else if (shDiff > 0.04) {
        newReport.score -= 10;
        newReport.details.push({ label: '轻微高低肩', value: 'Warning', status: 'warning', advice: '注意日常背包姿势，加强薄弱侧背部训练。' });
      } else {
          newReport.details.push({ label: '肩膀对称性', value: 'Excellent', status: 'normal', advice: '继续保持良好的姿势习惯。' });
      }

      // 2. 骨盆对称性
      const hipDiff = Math.abs(landmarks[23].y - landmarks[24].y);
      if (hipDiff > 0.05) {
        newReport.score -= 15;
        newReport.details.push({ label: '骨盆倾斜', value: '检测到偏斜', status: 'warning', advice: '加强单侧膝盖稳定性训练，检查是否有骨盆前倾或后倾。' });
      }
    } else {
      // 侧面分析: 头前伸 (Ear x vs Shoulder x 归一化后差距)
      const forwardHead = landmarks[7].x - landmarks[11].x; 
      if (forwardHead > 0.15) {
          newReport.score -= 25;
          newReport.details.push({ label: '严重头前伸', value: '严重', status: 'danger', advice: '这严重增加颈椎压力，需进行规律的收下巴训练。' });
      } else if (forwardHead > 0.08) {
          newReport.score -= 15;
          newReport.details.push({ label: '轻度头前伸', value: '轻度', status: 'warning', advice: '注意看电脑/手机的视线高度。' });
      }
    }

    if (newReport.score < 70) newReport.summary = '检测到多处姿态失衡';
    else if (newReport.score < 90) newReport.summary = '核心姿态良好，局部需微调';
    
    report.value = newReport;
    
    try {
        await apiClient.post('ai/posture-diagnosis/', {
            diagnosis_type: currentMode.value,
            score: newReport.score,
            summary: newReport.summary,
            detailed_report: newReport.details,
            landmarks_data: landmarks
        });
    } catch (e) { 
        console.error('History save failed', e); 
    }
    
    isAnalyzing.value = false;
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
