import { ref, onUnmounted } from 'vue';
import { Pose, type Results, POSE_CONNECTIONS } from '@mediapipe/pose';
import { Camera } from '@mediapipe/camera_utils';
import { drawConnectors, drawLandmarks } from '@mediapipe/drawing_utils';
import { calculateAngle, OneEuroFilter, normalizeLandmarks, matchPoseSignature } from '../utils/poseMatching';
import apiClient from '../api';

type VoiceCategory = 'count' | 'encourage' | 'corrective' | 'cadence';
type VoiceStyle = 'encouraging' | 'strict' | 'energetic';

interface SpokenEvent {
  ts: number;
  category: VoiceCategory;
  text: string;
}

const SAME_SENTENCE_COOLDOWN_MS = 4000;
const MIN_SPEAK_INTERVAL_MS = 1500;
const VARIETY_WINDOW_MS = 60000;

const VOICE_STYLES: Record<
  VoiceStyle,
  {
    rate: number;
    pitch: number;
    volume: number;
    encouragement: string[];
    corrective: string[];
    cadenceDown: string[];
    cadenceUp: string[];
  }
> = {
  encouraging: {
    rate: 1.15,
    pitch: 1.05,
    volume: 1,
    encouragement: ['很好，继续保持！', '节奏不错，稳住！', '干得漂亮，再来一组！'],
    corrective: ['膝盖和脚尖同向，动作更标准。', '背部挺直，核心收紧。', '幅度再完整一点。'],
    cadenceDown: ['慢一点下蹲', '稳住，继续下沉'],
    cadenceUp: ['发力起身', '起身，呼气'],
  },
  strict: {
    rate: 1.1,
    pitch: 0.95,
    volume: 1,
    encouragement: ['动作合格，继续。', '节奏达标，保持。', '完成不错，下一次更标准。'],
    corrective: ['不要借力，控制下放。', '膝盖别内扣，立刻修正。', '核心收紧，保持躯干稳定。'],
    cadenceDown: ['下蹲慢一点', '稳住，不要塌腰'],
    cadenceUp: ['发力起', '起身呼气'],
  },
  energetic: {
    rate: 1.3,
    pitch: 1.2,
    volume: 1,
    encouragement: ['太棒了，继续冲！', '状态在线，再来！', '很有力量，保持爆发！'],
    corrective: ['控制住，动作再标准一点！', '注意姿态，别急！', '稳住核心，继续干！'],
    cadenceDown: ['慢一点，稳住！', '下蹲控制住！'],
    cadenceUp: ['发力冲起来！', '起身呼气，走！'],
  },
};

const ERROR_TIP_MAP: Record<string, string> = {
  '膝盖内扣': '让膝盖方向与脚尖一致，起身时主动向外稳定膝盖。',
  '下蹲深度不足': '继续下沉到大腿接近平行地面，再发力起身。',
  '核心下塌': '收紧腹部和臀部，让肩-髋-踝尽量保持一条线。',
  '下放不充分': '离心阶段再慢一点，降低到目标深度再推起。',
  '骨盆下沉': '骨盆微后倾并收紧核心，避免腰部塌陷。',
  '手臂抬起不足': '向上阶段把手臂抬过头顶，动作幅度做完整。',
  '暂无明显错误': '当前动作整体稳定，继续保持节奏和呼吸。',
};

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
  const qualityLabel = ref('待评估');
  const qualityPercent = ref(0);
  const qualityColor = ref('#64748b');
  const standardStreak = ref(0);
  const bestStreak = ref(0);
  const commonErrorLabel = ref('暂无明显错误');
  const commonErrorTip = ref(ERROR_TIP_MAP['暂无明显错误']);
  const errorCounters = ref<Record<string, number>>({});
  const duration = ref(0);
  const isAnalyzingVlm = ref(false);
  const vlmAdvice = ref('');
  const latestLandmarks = ref<any[] | null>(null);
  const voiceStyle = ref<VoiceStyle>('encouraging');
  const stressModeEnabled = ref(false);
  const stressElapsedSeconds = ref(0);
  const voiceHitCount = ref({ count: 0, encourage: 0, corrective: 0, cadence: 0 });
  const voiceCoveredCategories = ref(0);
  const voiceTotalInLastMinute = ref(0);
  const voiceRepeatedInLastMinute = ref(0);
  const voiceCoveragePass = ref(false);
  const voiceQuietPass = ref(true);
  const voiceStressPass = ref(false);

  const VLM_COOLDOWN_MS = 15000; 
  let lastVlmTriggerTime = 0;    
  let hasCheckedFirstRep = false;

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
  let varietyTimer: number | null = null;
  let stressTimer: number | null = null;
  let stressStartAt: number | null = null;
  const spokenEvents: SpokenEvent[] = [];
  let lastPlankStreakSecond = 0;

  const lastSentenceAt = new Map<string, number>();
  const lastCategoryAt = new Map<VoiceCategory, number>();
  let lastSpeakAt = 0;

  const pickByStyle = (category: Exclude<VoiceCategory, 'count'>, phase?: 'down' | 'up') => {
    const stylePack = VOICE_STYLES[voiceStyle.value];
    if (category === 'cadence') {
      const phraseList = phase === 'down' ? stylePack.cadenceDown : stylePack.cadenceUp;
      return phraseList[Math.floor(Math.random() * phraseList.length)];
    }

    const phraseList = category === 'encourage' ? stylePack.encouragement : stylePack.corrective;
    return phraseList[Math.floor(Math.random() * phraseList.length)];
  };

  const shouldSkipSpeech = (text: string, now: number) => {
    if (!text) return true;
    if (now - lastSpeakAt < MIN_SPEAK_INTERVAL_MS) return true;

    const lastSame = lastSentenceAt.get(text);
    if (lastSame && now - lastSame < SAME_SENTENCE_COOLDOWN_MS) {
      return true;
    }
    return false;
  };

  const updateQualityBadge = (score: number) => {
    qualityPercent.value = Math.max(0, Math.min(100, score));
    if (score >= 90) {
      qualityLabel.value = '优秀';
      qualityColor.value = '#10b981';
      return;
    }
    if (score >= 80) {
      qualityLabel.value = '良好';
      qualityColor.value = '#22c55e';
      return;
    }
    if (score >= 70) {
      qualityLabel.value = '一般';
      qualityColor.value = '#f59e0b';
      return;
    }
    qualityLabel.value = '待改进';
    qualityColor.value = '#ef4444';
  };

  const markStandardOrBreakStreak = (score: number) => {
    if (score >= 85) {
      standardStreak.value += 1;
      if (standardStreak.value > bestStreak.value) {
        bestStreak.value = standardStreak.value;
      }
    } else {
      standardStreak.value = 0;
    }
  };

  const updateCommonErrorLabel = () => {
    let maxKey = '';
    let maxCount = 0;
    for (const [key, count] of Object.entries(errorCounters.value)) {
      if (count > maxCount) {
        maxCount = count;
        maxKey = key;
      }
    }
    commonErrorLabel.value = maxKey || '暂无明显错误';
    commonErrorTip.value = ERROR_TIP_MAP[commonErrorLabel.value] || '保持核心稳定，注意动作节奏。';
  };

  const markError = (label: string) => {
    errorCounters.value[label] = (errorCounters.value[label] || 0) + 1;
    updateCommonErrorLabel();
  };

  const refreshVoiceStressStats = () => {
    const now = Date.now();
    const windowStart = now - VARIETY_WINDOW_MS;

    while (spokenEvents.length > 0 && spokenEvents[0].ts < windowStart) {
      spokenEvents.shift();
    }

    let count = 0;
    let encourage = 0;
    let corrective = 0;
    let cadence = 0;
    let repeated = 0;
    const seenText = new Set<string>();

    for (const item of spokenEvents) {
      if (item.category === 'count') count += 1;
      if (item.category === 'encourage') encourage += 1;
      if (item.category === 'corrective') corrective += 1;
      if (item.category === 'cadence') cadence += 1;

      if (seenText.has(item.text)) {
        repeated += 1;
      } else {
        seenText.add(item.text);
      }
    }

    voiceHitCount.value = { count, encourage, corrective, cadence };
    voiceTotalInLastMinute.value = spokenEvents.length;
    voiceRepeatedInLastMinute.value = repeated;

    const covered = [count, encourage, corrective].filter((n) => n > 0).length;
    voiceCoveredCategories.value = covered;
    voiceCoveragePass.value = covered >= 3;

    const repeatRatio = spokenEvents.length > 0 ? repeated / spokenEvents.length : 0;
    voiceQuietPass.value = spokenEvents.length <= 18 && repeatRatio <= 0.35;
    voiceStressPass.value = voiceCoveragePass.value && voiceQuietPass.value;

    if (stressStartAt) {
      stressElapsedSeconds.value = Math.floor((now - stressStartAt) / 1000);
    }
  };

  const resetVoiceStressStats = () => {
    spokenEvents.length = 0;
    voiceHitCount.value = { count: 0, encourage: 0, corrective: 0, cadence: 0 };
    voiceCoveredCategories.value = 0;
    voiceTotalInLastMinute.value = 0;
    voiceRepeatedInLastMinute.value = 0;
    voiceCoveragePass.value = false;
    voiceQuietPass.value = true;
    voiceStressPass.value = false;
    stressElapsedSeconds.value = 0;
  };

  const speak = (text: string, category: VoiceCategory = 'encourage') => {
    if ('speechSynthesis' in window) {
      const now = Date.now();
      if (shouldSkipSpeech(text, now)) {
        return;
      }

      const stylePack = VOICE_STYLES[voiceStyle.value];
      const utterance = new SpeechSynthesisUtterance(text);
      utterance.lang = 'zh-CN';
      utterance.rate = stylePack.rate;
      utterance.pitch = stylePack.pitch;
      utterance.volume = stylePack.volume;
      window.speechSynthesis.speak(utterance);

      lastSpeakAt = now;
      lastSentenceAt.set(text, now);
      lastCategoryAt.set(category, now);
      if (stressModeEnabled.value) {
        spokenEvents.push({ ts: now, category, text });
        refreshVoiceStressStats();
      }
    }
  };

  const speakCountdown = (count: number) => speak(String(count), 'count');
  const speakEncouragement = () => speak(pickByStyle('encourage'), 'encourage');
  const speakCorrection = () => speak(pickByStyle('corrective'), 'corrective');
  const speakCadence = (phase: 'down' | 'up') => speak(pickByStyle('cadence', phase), 'cadence');
  const scheduleSpeak = (fn: () => void, delay = 1800) => {
    window.setTimeout(() => {
      if (isUpdating.value) fn();
    }, delay);
  };

  const maybeEnsureVoiceVariety = () => {
    if (!isUpdating.value) return;

    const now = Date.now();
    const categories: VoiceCategory[] = ['count', 'encourage', 'corrective'];
    const missing = categories.filter((category) => {
      const lastAt = lastCategoryAt.get(category);
      return !lastAt || now - lastAt > VARIETY_WINDOW_MS;
    });

    if (missing.length === 0) return;

    const target = missing[0];
    if (target === 'count') {
      speak('当前计数，' + String(repCount.value), 'count');
      return;
    }
    if (target === 'encourage') {
      speakEncouragement();
      return;
    }
    speakCorrection();
  };

  const clearCoachTimer = () => {
    if (coachTimer) {
      window.clearInterval(coachTimer);
      coachTimer = null;
    }
    if (varietyTimer) {
      window.clearInterval(varietyTimer);
      varietyTimer = null;
    }
    if (stressTimer) {
      window.clearInterval(stressTimer);
      stressTimer = null;
    }
  };

  const startCoachTimer = () => {
    clearCoachTimer();
    coachTimer = window.setInterval(() => {
      const idleTime = Date.now() - lastStateChange;
      if (idleTime > 8000 && isUpdating.value) {
        if (state === 'UP') {
          speakEncouragement();
        } else {
          speakCadence('up');
        }
        lastStateChange = Date.now();
      }
    }, 1000);

    varietyTimer = window.setInterval(() => {
      maybeEnsureVoiceVariety();
    }, 10000);

    stressTimer = window.setInterval(() => {
      if (stressModeEnabled.value) {
        refreshVoiceStressStats();
      }
    }, 1000);
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

  const analyzeWithVisionModel = async () => {
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
        exercise_type: exerciseMode.value,
        landmarks: latestLandmarks.value,
        motion_metrics: {
          rep_progress: repProgress.value,
          last_score: lastScore.value,
          rep_count: repCount.value,
        },
      });

      const advice = response.data?.advice || '已完成分析，请继续保持训练节奏';
      vlmAdvice.value = advice;
      feedback.value = `🤖 ${advice}`;
      speak(advice, 'corrective');
    } catch (err: any) {
      const message = err?.response?.data?.detail || '视觉大模型分析失败，请稍后重试';
      feedback.value = `⚠️ ${message}`;
    } finally {
      isAnalyzingVlm.value = false;
    }
  };

  const tryTriggerVlmAnalysis = (currentScore: number) => {
    const now = Date.now();

    if (isAnalyzingVlm.value || (now - lastVlmTriggerTime < VLM_COOLDOWN_MS)) {
      return;
    }

    const isFirstRep = !hasCheckedFirstRep; 
    const isBadForm = currentScore < 80;    

    if (isFirstRep || isBadForm) {
      lastVlmTriggerTime = now;
      hasCheckedFirstRep = true;
      
      console.log(`📸 触发智能抽帧! 原因: ${isFirstRep ? '首个动作' : '动作变形'}, 相似度得分: ${currentScore}`);

      analyzeWithVisionModel(); 
    }
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
      
      const smoothedLandmarks = results.poseLandmarks.map((lm, i) => {
        if (i >= 33) return lm;
        return {
          ...lm,
          x: landmarkFilters[i].x.filter(lm.x, now),
          y: landmarkFilters[i].y.filter(lm.y, now),
          z: landmarkFilters[i].z.filter(lm.z, now),
        };
      });
      latestLandmarks.value = smoothedLandmarks;

      const skeletonColor = lastScore.value > 88 ? 'rgba(0, 255, 100, 0.6)' : 'rgba(255, 165, 0, 0.6)';
      drawConnectors(canvasCtx, smoothedLandmarks, POSE_CONNECTIONS, { color: skeletonColor, lineWidth: 5 });
      drawLandmarks(canvasCtx, smoothedLandmarks, { 
        color: '#FFFFFF', 
        lineWidth: 1, 
        radius: (data: any) => (data.index > 10 ? 3 : 1) 
      });

      if (exerciseMode.value === 'squat') {
        const angle = calculateAngle(smoothedLandmarks[24], smoothedLandmarks[26], smoothedLandmarks[28]);
        if (angle) {
          const smoothedAngle = angleFilter.filter(angle, now);
          const leftKneeInward = Math.abs(smoothedLandmarks[25].x - smoothedLandmarks[27].x) < 0.035;
          const rightKneeInward = Math.abs(smoothedLandmarks[26].x - smoothedLandmarks[28].x) < 0.035;
          repProgress.value = Math.floor(progressFilter.filter(Math.max(0, Math.min(100, (170 - smoothedAngle) / 80 * 100)), now));

          if (smoothedAngle < 105 && state === 'UP') {
            state = 'DOWN';
            feedback.value = '下沉到位！';
            speakCadence('down');
            lastStateChange = now;
            
            const signatureScore = matchPoseSignature(smoothedLandmarks, 'squat_down');
            lastScore.value = Math.round(signatureScore * 100);
            updateQualityBadge(lastScore.value);

            if (leftKneeInward || rightKneeInward) {
              markError('膝盖内扣');
            }
            if (smoothedAngle > 120) {
              markError('下蹲深度不足');
            }

            if (lastScore.value < 85) {
              speakCorrection();
            }

            tryTriggerVlmAnalysis(lastScore.value);

          } else if (smoothedAngle > 155 && state === 'DOWN') {
            state = 'UP';
            repCount.value++;
            markStandardOrBreakStreak(lastScore.value);
            speakCountdown(repCount.value);
            if (repCount.value % 2 === 1) {
              scheduleSpeak(() => speakCadence('up'), 1800);
            }
            if (repCount.value % 2 === 0 || lastScore.value > 90) {
              scheduleSpeak(() => speakEncouragement(), 3200);
            }
            feedback.value = lastScore.value > 90 ? '完美动作！' : '保持呼吸';
            lastStateChange = now;
          }
        }
      } else if (exerciseMode.value === 'pushup') {
          const angle = calculateAngle(smoothedLandmarks[12], smoothedLandmarks[14], smoothedLandmarks[16]);
          if (angle) {
            const smoothed = angleFilter.filter(angle, now);
            const shoulderY = (smoothedLandmarks[11].y + smoothedLandmarks[12].y) / 2;
            const hipY = (smoothedLandmarks[23].y + smoothedLandmarks[24].y) / 2;
            repProgress.value = Math.floor(progressFilter.filter(Math.max(0, Math.min(100, (160 - smoothed) / 85 * 100)), now));
            
            if (smoothed < 95 && state === 'UP') {
                state = 'DOWN';
                feedback.value = '准备撑起！';
                speakCadence('down');
                lastStateChange = now;
                const signatureScore = matchPoseSignature(smoothedLandmarks, 'pushup_down');
                lastScore.value = Math.round(signatureScore * 100);
                updateQualityBadge(lastScore.value);

                if (hipY > shoulderY + 0.12) {
                  markError('核心下塌');
                }
                if (smoothed > 125) {
                  markError('下放不充分');
                }

                if (lastScore.value < 85) {
                  speakCorrection();
                }

                tryTriggerVlmAnalysis(lastScore.value);

            } else if (smoothed > 150 && state === 'DOWN') {
                state = 'UP';
                repCount.value++;
              markStandardOrBreakStreak(lastScore.value);
                speakCountdown(repCount.value);
                if (repCount.value % 2 === 1) {
                  scheduleSpeak(() => speakCadence('up'), 1800);
                }
                if (repCount.value % 2 === 0 || lastScore.value > 90) {
                  scheduleSpeak(() => speakEncouragement(), 3200);
                }
                lastStateChange = now;
            }
          }
      } else if (exerciseMode.value === 'plank') {
          const signatureScore = matchPoseSignature(smoothedLandmarks, 'plank');
          lastScore.value = Math.round(signatureScore * 100);
          updateQualityBadge(lastScore.value);
          const shoulderY = (smoothedLandmarks[11].y + smoothedLandmarks[12].y) / 2;
          const hipY = (smoothedLandmarks[23].y + smoothedLandmarks[24].y) / 2;
          
          if (lastScore.value > 85) {
              if (!plankStartTime) plankStartTime = now;
              duration.value = Math.floor((now - plankStartTime) / 1000);
              feedback.value = `坚持住！稳定性: ${lastScore.value}%`;
              repProgress.value = 100;
              if (duration.value > lastPlankStreakSecond) {
                lastPlankStreakSecond = duration.value;
                standardStreak.value += 1;
                if (standardStreak.value > bestStreak.value) {
                  bestStreak.value = standardStreak.value;
                }
              }
          } else {
              plankStartTime = null;
              standardStreak.value = 0;
              lastPlankStreakSecond = 0;
              feedback.value = '⚠️ 请保持身体平直';
              if (hipY > shoulderY + 0.1) {
                markError('骨盆下沉');
              }
              speakCorrection();
              repProgress.value = lastScore.value;

              tryTriggerVlmAnalysis(lastScore.value);
          }
      } else if (exerciseMode.value === 'jumping_jack') {
          const score = matchPoseSignature(smoothedLandmarks, 'jumping_jack_up');
          const avgHandY = (smoothedLandmarks[15].y + smoothedLandmarks[16].y) / 2;
          const headY = smoothedLandmarks[0].y;
          
          if (avgHandY < headY && score > 0.7 && state === 'UP') {
              state = 'DOWN';
              speakCadence('down');
              lastStateChange = now;
              lastScore.value = Math.round(score * 100);
              updateQualityBadge(lastScore.value);

              if (avgHandY > headY + 0.08) {
                markError('手臂抬起不足');
              }

              if (lastScore.value < 85) {
                speakCorrection();
              }

              tryTriggerVlmAnalysis(lastScore.value);

          } else if (avgHandY > headY + 0.2 && state === 'DOWN') {
              state = 'UP';
              repCount.value++;
              markStandardOrBreakStreak(lastScore.value);
              speakCountdown(repCount.value);
              if (repCount.value % 2 === 1) {
                scheduleSpeak(() => speakCadence('up'), 1800);
              }
              if (repCount.value % 2 === 0 || lastScore.value > 90) {
                scheduleSpeak(() => speakEncouragement(), 3200);
              }
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
        width: 1280, 
        height: 720
      });
      
      await camera.start();
      isUpdating.value = true;
      if (stressModeEnabled.value) {
        stressStartAt = Date.now();
        resetVoiceStressStats();
      }
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
    stressStartAt = null;
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
    qualityLabel,
    qualityPercent,
    qualityColor,
    standardStreak,
    bestStreak,
    commonErrorLabel,
    commonErrorTip,
    duration,
    isAnalyzingVlm,
    vlmAdvice,
    initPose,
    analyzeWithVisionModel,
    stopPose,
    voiceStyle,
    stressModeEnabled,
    stressElapsedSeconds,
    voiceHitCount,
    voiceCoveredCategories,
    voiceTotalInLastMinute,
    voiceRepeatedInLastMinute,
    voiceCoveragePass,
    voiceQuietPass,
    voiceStressPass,
    resetCount: () => {
      repCount.value = 0;
      standardStreak.value = 0;
      bestStreak.value = 0;
      commonErrorLabel.value = '暂无明显错误';
      commonErrorTip.value = ERROR_TIP_MAP['暂无明显错误'];
      errorCounters.value = {};
      qualityLabel.value = '待评估';
      qualityPercent.value = 0;
      qualityColor.value = '#64748b';
      duration.value = 0;
      plankStartTime = null;
      lastPlankStreakSecond = 0;
      state = 'UP';
      feedback.value = '请就位';
      vlmAdvice.value = '';
      resetVoiceStressStats();
      stressStartAt = stressModeEnabled.value ? Date.now() : null;

      lastVlmTriggerTime = 0;
      hasCheckedFirstRep = false;
    }
  };
}