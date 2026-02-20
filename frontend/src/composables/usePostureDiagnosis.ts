import { ref } from 'vue';
import { Pose, type Results } from '@mediapipe/pose';
import { Camera } from '@mediapipe/camera_utils';
import { drawConnectors, drawLandmarks, POSE_CONNECTIONS } from '@mediapipe/drawing_utils';
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
  const videoElement = ref<HTMLVideoElement | null>(null);
  const canvasElement = ref<HTMLCanvasElement | null>(null);
  const isLoaded = ref(false);
  const isAnalyzing = ref(false);
  const currentMode = ref<'front' | 'side'>('front');
  const lastResults = ref<Results | null>(null);
  const report = ref<PostureReport | null>(null);

  let pose: Pose | null = null;
  let camera: Camera | null = null;

  const initPose = async () => {
    pose = new Pose({
      locateFile: (file) => `https://cdn.jsdelivr.net/npm/@mediapipe/pose/${file}`,
    });

    pose.setOptions({
      modelComplexity: 1,
      smoothLandmarks: true,
      enableSegmentation: false,
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
        width: 640,
        height: 480,
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
      drawConnectors(ctx, results.poseLandmarks, POSE_CONNECTIONS, { color: '#00FF00', lineWidth: 2 });
      drawLandmarks(ctx, results.poseLandmarks, { color: '#FF0000', lineWidth: 1 });
    }
    ctx.restore();
  };

  const analyze = async () => {
    if (!lastResults.value?.poseLandmarks) return;
    isAnalyzing.value = true;
    
    const landmarks = lastResults.value.poseLandmarks;
    const newReport: PostureReport = {
      score: 100,
      summary: '姿态良好',
      details: []
    };

    if (currentMode.value === 'front') {
      // 1. 肩膀对称性 (Shoulder 11, 12)
      const leftShoulder = landmarks[11];
      const rightShoulder = landmarks[12];
      const shDiff = Math.abs(leftShoulder.y - rightShoulder.y);
      
      if (shDiff > 0.03) {
        newReport.score -= 15;
        newReport.details.push({
          label: '高低肩',
          value: '显著',
          status: 'danger',
          advice: '建议练习单侧抗阻训练和牵拉斜方肌。'
        });
      } else if (shDiff > 0.015) {
        newReport.score -= 5;
        newReport.details.push({
          label: '肩膀对称性',
          value: '轻微偏移',
          status: 'warning',
          advice: '日常注意背包姿势，多做扩胸运动。'
        });
      } else {
        newReport.details.push({
          label: '肩膀对称性',
          value: '正常曲线',
          status: 'normal',
          advice: '保持良好姿势。'
        });
      }

      // 2. 骨盆对称性 (Hip 23, 24)
      const leftHip = landmarks[23];
      const rightHip = landmarks[24];
      const hipDiff = Math.abs(leftHip.y - rightHip.y);
      if (hipDiff > 0.02) {
        newReport.score -= 10;
        newReport.details.push({
          label: '骨盆倾斜',
          value: '检测到偏斜',
          status: 'warning',
          advice: '检查是否有长短腿风险，加强核心支撑力。'
        });
      }

      // 3. 头部倾斜 (Eye 1, 4)
      const leftEye = landmarks[1];
      const rightEye = landmarks[4];
      const eyeDiff = Math.abs(leftEye.y - rightEye.y);
      if (eyeDiff > 0.01) {
          newReport.score -= 5;
          newReport.details.push({
              label: '头部侧倾',
              value: '轻微倾斜',
              status: 'warning',
              advice: '注意阅读和工作时的颈部中立位。'
          });
      }
    } else {
      // 侧面分析: 重点是头前伸和骨盆前倾
      const ear = landmarks[7]; // 左耳
      const shoulder = landmarks[11]; // 左肩
      const hip = landmarks[23]; // 左臀
      
      // 1. 头前伸 (Ear x vs Shoulder x)
      const forwardHead = ear.x - shoulder.x; 
      if (forwardHead > 0.05) {
          newReport.score -= 20;
          newReport.details.push({
              label: '头前伸 (颈椎负担)',
              value: '严重',
              status: 'danger',
              advice: '这是颈椎病的高危因素，请务必进行颈深屈肌训练。'
          });
      } else if (forwardHead > 0.02) {
          newReport.score -= 10;
          newReport.details.push({
              label: '头前伸',
              value: '轻度',
              status: 'warning',
              advice: '注意使用手机时的视线高度，多做收核心练习。'
          });
      }

      // 2. 圆肩 (Shoulder vs Hip x)
      const xDiff = Math.abs(shoulder.x - hip.x);
      if (xDiff > 0.08) {
          newReport.score -= 15;
          newReport.details.push({
              label: '圆肩/驼峰',
              value: '明显',
              status: 'warning',
              advice: '加强后背肌肉（如划船动作），拉伸胸小肌。'
          });
      }
    }

    if (newReport.score < 70) newReport.summary = '检测到多项失衡';
    else if (newReport.score < 90) newReport.summary = '存在细微姿态风险';
    
    report.value = newReport;
    
    // 保存到后端
    try {
        await apiClient.post('ai/posture-diagnosis/', {
            diagnosis_type: currentMode.value,
            score: newReport.score,
            summary: newReport.summary,
            detailed_report: newReport.details,
            landmarks_data: landmarks
        });
    } catch (e) {
        console.error('Failed to save diagnosis', e);
    }
    
    isAnalyzing.value = false;
  };

  const stop = () => {
      camera?.stop();
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
