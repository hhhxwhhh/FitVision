import { computed, ref } from 'vue';

/** Coach tips for every fault key the pose engine can emit. */
export const ERROR_TIP_MAP: Record<string, string> = {
  '膝盖内扣': '让膝盖方向与脚尖一致，起身时主动向外稳定膝盖。',
  '下蹲深度不足': '继续下沉到大腿接近平行地面，再发力起身。',
  '核心下塌': '收紧腹部和臀部，让肩-髋-踝尽量保持一条线。',
  '下放不充分': '离心阶段再慢一点，降低到目标深度再推起。',
  '骨盆下沉': '骨盆微后倾并收紧核心，避免腰部塌陷。',
  '手臂抬起不足': '向上阶段把手臂抬过头顶，动作幅度做完整。',
  '躯干过度前倾': '挺胸并收紧核心，让躯干在可控范围内保持直立。',
  '左右不对称': '让身体两侧同步发力，必要时降低重量或放慢节奏。',
  '臀部过高': '降低髋部，让肩、髋、踝重新回到一条直线上。',
  '身体未成直线': '收紧腹部和臀部，避免塌腰或撅臀。',
  '肘部未对齐': '让肘部位于肩部正下方，前臂保持稳定支撑。',
  '身体晃动': '放慢呼吸、收紧核心，减少身体前后左右晃动。',
  '双腿张开不足': '落地时双脚再打开一些，保持与肩同宽以上。',
  '弓步步幅过小': '前后脚再拉开一些，让前膝落在脚踝正上方。',
  '弓步步幅过大': '收回一点步幅，避免髋部被过度拉伸而失去稳定。',
  '重心偏向一侧': '两侧均衡发力，保持髋部摆正后再下沉。',
  '上卷幅度不足': '用腹部把胸廓继续向骨盆方向卷，肩胛离地再高一点。',
  '髋部起伏过大': '髋部贴住地面，只让上半身抬起，减少腿部代偿。',
  '腿部角度不稳': '固定双脚与屈膝角度，让腹部单独完成卷起。',
  '关键点不可见': '请让全身进入画面，保持光线充足并避免遮挡。',
  '暂无明显错误': '当前动作整体稳定，继续保持节奏和呼吸。',
};

export const NO_ERROR_LABEL = '暂无明显错误';
export const FALLBACK_TIP = '保持核心稳定，注意动作节奏。';

/** Standard-or-break threshold used to grow the form streak. */
export const STANDARD_REP_SCORE = 85;

export interface QualityBadge {
  label: string;
  percent: number;
  color: string;
}

/** Maps a form score onto the badge shown next to the live preview. */
export const scoreQualityBadge = (score: number): QualityBadge => {
  const percent = Math.max(0, Math.min(100, score));
  if (score >= 90) return { label: '优秀', percent, color: '#15803d' };
  if (score >= 80) return { label: '良好', percent, color: '#16a34a' };
  if (score >= 70) return { label: '一般', percent, color: '#b45309' };
  return { label: '待改进', percent, color: '#b91c1c' };
};

/** Picks the most frequent fault; ties resolve deterministically by insertion order. */
export const mostFrequentError = (counters: Record<string, number>): string => {
  let top = '';
  let topCount = 0;
  for (const [key, count] of Object.entries(counters)) {
    if (count > topCount) {
      top = key;
      topCount = count;
    }
  }
  return top || NO_ERROR_LABEL;
};

/**
 * Owns the per-session form metrics: quality badge, standard-rep streak and
 * the running tally of form faults. Split out of `usePoseDetection` so the
 * scoring logic can be tested without a camera or MediaPipe.
 */
export function useFormMetrics() {
  const qualityLabel = ref('待评估');
  const qualityPercent = ref(0);
  const qualityColor = ref('#64748b');
  const standardStreak = ref(0);
  const bestStreak = ref(0);
  const errorCounters = ref<Record<string, number>>({});
  const commonErrorLabel = ref(NO_ERROR_LABEL);
  const commonErrorTip = ref(ERROR_TIP_MAP[NO_ERROR_LABEL] ?? FALLBACK_TIP);

  const hasErrors = computed(() => Object.keys(errorCounters.value).length > 0);

  const updateQualityBadge = (score: number) => {
    const badge = scoreQualityBadge(score);
    qualityLabel.value = badge.label;
    qualityPercent.value = badge.percent;
    qualityColor.value = badge.color;
  };

  const growStreak = () => {
    standardStreak.value += 1;
    if (standardStreak.value > bestStreak.value) {
      bestStreak.value = standardStreak.value;
    }
  };

  const breakStreak = () => {
    standardStreak.value = 0;
  };

  /** Grows the streak on a clean rep and breaks it otherwise. */
  const registerRep = (score: number) => {
    if (score >= STANDARD_REP_SCORE) growStreak();
    else breakStreak();
  };

  const updateCommonErrorLabel = () => {
    commonErrorLabel.value = mostFrequentError(errorCounters.value);
    commonErrorTip.value = ERROR_TIP_MAP[commonErrorLabel.value] ?? FALLBACK_TIP;
  };

  /** Records newly surfaced faults so repeated ones are not double counted. */
  const recordFaults = (labels: readonly string[]) => {
    const unique = new Set(labels);
    for (const label of unique) {
      errorCounters.value[label] = (errorCounters.value[label] || 0) + 1;
    }
    updateCommonErrorLabel();
  };

  const reset = () => {
    qualityLabel.value = '待评估';
    qualityPercent.value = 0;
    qualityColor.value = '#64748b';
    standardStreak.value = 0;
    bestStreak.value = 0;
    errorCounters.value = {};
    commonErrorLabel.value = NO_ERROR_LABEL;
    commonErrorTip.value = ERROR_TIP_MAP[NO_ERROR_LABEL] ?? FALLBACK_TIP;
  };

  return {
    qualityLabel,
    qualityPercent,
    qualityColor,
    standardStreak,
    bestStreak,
    errorCounters,
    commonErrorLabel,
    commonErrorTip,
    hasErrors,
    updateQualityBadge,
    growStreak,
    breakStreak,
    registerRep,
    recordFaults,
    reset,
  };
}
