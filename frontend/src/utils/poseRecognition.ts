/**
 * Pose recognition engine.
 *
 * The previous implementation counted reps with single-frame angle thresholds
 * and scored form with a fixed cosine signature. That is fragile: camera
 * distance, mirroring, one-sided landmarks and jitter could all change the
 * result. This module turns the raw MediaPipe landmarks into a body-scale
 * normalised representation, detects the camera view, and runs an explicit
 * phase state machine with dwell time, minimum range of motion and confidence
 * gating. Form scoring is exercise-specific and combines several independent
 * signals (range of motion, alignment, symmetry, stability).
 */

export interface Landmark {
  x: number;
  y: number;
  z: number;
  visibility?: number;
}

export type ExerciseMode = 'squat' | 'pushup' | 'jumping_jack' | 'plank';
export type PosePhase = 'up' | 'down' | 'holding';
export type ViewOrientation = 'front' | 'side' | 'unknown';

export interface FormFault {
  key: string;
  severity: number;
}

export interface AnalysisFrame {
  phase: PosePhase;
  /** 0-100 movement progress, where 100 is the deepest/strongest position. */
  progress: number;
  /** Smoothed live form score. */
  formScore: number;
  repCompleted: boolean;
  repScore: number;
  enteredDown: boolean;
  enteredUp: boolean;
  faults: FormFault[];
  confidence: number;
  view: ViewOrientation;
  primaryAngle: number | null;
  isHolding: boolean;
  holdSeconds: number;
}

export interface ExerciseAnalyzer {
  reset(): void;
  update(landmarks: Landmark[], timestamp: number, aspectRatio?: number): AnalysisFrame;
}

const NOSE = 0;
const LEFT_SHOULDER = 11;
const RIGHT_SHOULDER = 12;
const LEFT_ELBOW = 13;
const RIGHT_ELBOW = 14;
const LEFT_WRIST = 15;
const RIGHT_WRIST = 16;
const LEFT_HIP = 23;
const RIGHT_HIP = 24;
const LEFT_KNEE = 25;
const RIGHT_KNEE = 26;
const LEFT_ANKLE = 27;
const RIGHT_ANKLE = 28;

const DEFAULT_ASPECT_RATIO = 16 / 9;
const VISIBILITY_THRESHOLD = 0.35;

export const clamp = (value: number, min = 0, max = 100) =>
  Math.min(max, Math.max(min, value));

export const mapRange = (value: number, inMin: number, inMax: number) => {
  if (inMax === inMin) return value >= inMax ? 100 : 0;
  return clamp(((value - inMin) / (inMax - inMin)) * 100);
};

export const distance = (a: Landmark, b: Landmark) => Math.hypot(a.x - b.x, a.y - b.y);

const midpoint = (a: Landmark, b: Landmark): Landmark => ({
  x: (a.x + b.x) / 2,
  y: (a.y + b.y) / 2,
  z: (a.z + b.z) / 2,
  visibility: Math.min(a.visibility ?? 1, b.visibility ?? 1),
});

const isVisible = (landmark: Landmark | undefined, threshold = VISIBILITY_THRESHOLD) =>
  Boolean(landmark) && (landmark!.visibility ?? 1) >= threshold;

/**
 * Angle between three points. Returns null when any point is missing or not
 * visible enough, so callers never silently score a half-visible skeleton.
 */
export function angleDeg(a: Landmark, b: Landmark, c: Landmark): number | null {
  if (!isVisible(a) || !isVisible(b) || !isVisible(c)) return null;
  const abx = a.x - b.x;
  const aby = a.y - b.y;
  const cbx = c.x - b.x;
  const cby = c.y - b.y;
  const magnitude = Math.hypot(abx, aby) * Math.hypot(cbx, cby);
  if (magnitude < 1e-6) return null;
  const cosine = clamp((abx * cbx + aby * cby) / magnitude, -1, 1);
  return (Math.acos(cosine) * 180) / Math.PI;
}

const angleBetweenVectors = (
  v1: { x: number; y: number },
  v2: { x: number; y: number },
): number => {
  const magnitude = Math.hypot(v1.x, v1.y) * Math.hypot(v2.x, v2.y);
  if (magnitude < 1e-6) return 0;
  const cosine = clamp((v1.x * v2.x + v1.y * v2.y) / magnitude, -1, 1);
  return (Math.acos(cosine) * 180) / Math.PI;
};

const combineSideAngles = (left: number | null, right: number | null) => {
  if (left == null && right == null) return { value: null as number | null, diff: 0 };
  if (left == null) return { value: right as number | null, diff: 0 };
  if (right == null) return { value: left as number | null, diff: 0 };
  return { value: (left + right) / 2, diff: Math.abs(left - right) };
};

const weightedScore = (parts: Array<[number, number]>) => {
  const totalWeight = parts.reduce((sum, [, weight]) => sum + weight, 0);
  if (totalWeight <= 0) return 0;
  return parts.reduce((sum, [score, weight]) => sum + score * weight, 0) / totalWeight;
};

const visibilityConfidence = (
  landmarks: Landmark[],
  indices: number[],
  threshold = VISIBILITY_THRESHOLD,
) => {
  let visible = 0;
  let total = 0;
  for (const index of indices) {
    const value = landmarks[index]?.visibility ?? 1;
    total += value;
    if (value >= threshold) visible += 1;
  }
  if (indices.length === 0) return 0;
  return clamp(((visible / indices.length) * 0.7 + (total / indices.length) * 0.3) * 100) / 100;
};

const MISSING_LANDMARK: Landmark = { x: 0, y: 0, z: 0, visibility: 0 };

interface BodyFrame {
  lm: Landmark[];
  at: (index: number) => Landmark;
  midShoulder: Landmark;
  midHip: Landmark;
  midAnkle: Landmark;
  torso: number;
  shoulderWidth: number;
  hipWidth: number;
  view: ViewOrientation;
  confidence: (indices: number[], threshold?: number) => number;
}

/**
 * Convert normalised MediaPipe coordinates to an isotropic metric space.
 * MediaPipe normalises x by image width and y by image height, so angles are
 * distorted when the two are used directly. Multiplying x/z by the aspect
 * ratio fixes that without changing the scale-invariant ratios we rely on.
 */
const buildBody = (raw: Landmark[], aspectRatio = DEFAULT_ASPECT_RATIO): BodyFrame => {
  const aspect = Number.isFinite(aspectRatio) && aspectRatio > 0 ? aspectRatio : DEFAULT_ASPECT_RATIO;
  const lm = raw.map((point) => ({
    ...point,
    x: point.x * aspect,
    y: point.y,
    z: point.z * aspect,
  }));
  const at = (index: number): Landmark => lm[index] ?? MISSING_LANDMARK;

  const midShoulder = midpoint(at(LEFT_SHOULDER), at(RIGHT_SHOULDER));
  const midHip = midpoint(at(LEFT_HIP), at(RIGHT_HIP));
  const midAnkle = midpoint(at(LEFT_ANKLE), at(RIGHT_ANKLE));
  const shoulderWidth = distance(at(LEFT_SHOULDER), at(RIGHT_SHOULDER));
  const hipWidth = distance(at(LEFT_HIP), at(RIGHT_HIP));
  const torso = Math.max(distance(midShoulder, midHip), 1e-4);
  const widthRatio = (shoulderWidth + hipWidth) / 2 / torso;

  let view: ViewOrientation = 'unknown';
  if (widthRatio >= 0.52) view = 'front';
  else if (widthRatio > 0 && widthRatio <= 0.3) view = 'side';

  return {
    lm,
    at,
    midShoulder,
    midHip,
    midAnkle,
    torso,
    shoulderWidth,
    hipWidth,
    view,
    confidence: (indices, threshold) => visibilityConfidence(lm, indices, threshold),
  };
};

/**
 * Signed vertical distance from a point to the line a-b. In image
 * coordinates positive means the point is below the line (hip sagging).
 */
const verticalOffsetFromLine = (point: Landmark, a: Landmark, b: Landmark) => {
  const dx = b.x - a.x;
  if (Math.abs(dx) < 1e-4) return point.y - (a.y + b.y) / 2;
  const t = (point.x - a.x) / dx;
  const lineY = a.y + (b.y - a.y) * t;
  return point.y - lineY;
};

interface MeasureResult {
  load: number;
  confidence: number;
  view: ViewOrientation;
  score: number;
  faults: FormFault[];
  primaryAngle: number | null;
  metrics: Record<string, number | null>;
}

const createMeasureResult = (
  body: BodyFrame,
  values: Omit<MeasureResult, 'confidence' | 'view'>,
  indices: number[],
): MeasureResult => ({
  ...values,
  confidence: body.confidence(indices),
  view: body.view,
});

const measureSquat = (body: BodyFrame): MeasureResult => {
  const at = body.at;
  const left = angleDeg(at(LEFT_HIP), at(LEFT_KNEE), at(LEFT_ANKLE));
  const right = angleDeg(at(RIGHT_HIP), at(RIGHT_KNEE), at(RIGHT_ANKLE));
  const { value: knee, diff } = combineSideAngles(left, right);
  const indices = [
    LEFT_SHOULDER,
    RIGHT_SHOULDER,
    LEFT_HIP,
    RIGHT_HIP,
    LEFT_KNEE,
    RIGHT_KNEE,
    LEFT_ANKLE,
    RIGHT_ANKLE,
  ];

  if (knee == null) {
    return createMeasureResult(
      body,
      {
        load: 0,
        score: 0,
        faults: [{ key: '关键点不可见', severity: 1 }],
        primaryAngle: null,
        metrics: {},
      },
      indices,
    );
  }

  const load = mapRange(knee, 165, 90);
  const depthScore = mapRange(knee, 140, 95);
  const torsoVector = {
    x: body.midShoulder.x - body.midHip.x,
    y: body.midShoulder.y - body.midHip.y,
  };
  const torsoLean = angleBetweenVectors(torsoVector, { x: 0, y: -1 });
  const torsoScore = mapRange(torsoLean, 70, 20);
  const symmetryScore = mapRange(diff, 30, 8);

  let kneeTrackingScore = 100;
  let kneeCollapse = 0;
  if (body.view === 'front') {
    const kneeSpan = Math.abs(at(LEFT_KNEE).x - at(RIGHT_KNEE).x);
    const ankleSpan = Math.abs(at(LEFT_ANKLE).x - at(RIGHT_ANKLE).x);
    if (ankleSpan > 1e-4) {
      kneeCollapse = clamp((ankleSpan - kneeSpan) / (ankleSpan * 0.45), 0, 1);
      kneeTrackingScore = (1 - kneeCollapse) * 100;
    }
  }

  const faults: FormFault[] = [];
  if (load > 25) {
    if (knee > 118) {
      faults.push({ key: '下蹲深度不足', severity: clamp((knee - 118) / 30, 0, 1) });
    }
    if (torsoLean > 55) {
      faults.push({ key: '躯干过度前倾', severity: clamp((torsoLean - 55) / 25, 0, 1) });
    }
    if (diff > 18) {
      faults.push({ key: '左右不对称', severity: clamp((diff - 18) / 20, 0, 1) });
    }
    if (body.view === 'front' && kneeCollapse > 0.35) {
      faults.push({ key: '膝盖内扣', severity: kneeCollapse });
    }
  }

  const score =
    body.view === 'front'
      ? weightedScore([
          [depthScore, 0.35],
          [torsoScore, 0.2],
          [kneeTrackingScore, 0.3],
          [symmetryScore, 0.15],
        ])
      : body.view === 'side'
        ? weightedScore([
            [depthScore, 0.5],
            [torsoScore, 0.35],
            [symmetryScore, 0.15],
          ])
        : weightedScore([
            [depthScore, 0.45],
            [torsoScore, 0.3],
            [kneeTrackingScore, 0.1],
            [symmetryScore, 0.15],
          ]);

  return createMeasureResult(
    body,
    {
      load,
      score,
      faults,
      primaryAngle: knee,
      metrics: {
        left_knee: left,
        right_knee: right,
        torso_lean: torsoLean,
        knee_collapse: kneeCollapse,
      },
    },
    indices,
  );
};

const measurePushup = (body: BodyFrame): MeasureResult => {
  const at = body.at;
  const left = angleDeg(at(LEFT_SHOULDER), at(LEFT_ELBOW), at(LEFT_WRIST));
  const right = angleDeg(at(RIGHT_SHOULDER), at(RIGHT_ELBOW), at(RIGHT_WRIST));
  const { value: elbow, diff } = combineSideAngles(left, right);
  const bodyLine = angleDeg(body.midShoulder, body.midHip, body.midAnkle);
  const indices = [
    LEFT_SHOULDER,
    RIGHT_SHOULDER,
    LEFT_ELBOW,
    RIGHT_ELBOW,
    LEFT_WRIST,
    RIGHT_WRIST,
    LEFT_HIP,
    RIGHT_HIP,
    LEFT_ANKLE,
    RIGHT_ANKLE,
  ];

  if (elbow == null) {
    return createMeasureResult(
      body,
      {
        load: 0,
        score: 0,
        faults: [{ key: '关键点不可见', severity: 1 }],
        primaryAngle: null,
        metrics: {},
      },
      indices,
    );
  }

  const load = mapRange(elbow, 160, 85);
  const depthScore = mapRange(elbow, 130, 85);
  const hipOffset = verticalOffsetFromLine(body.midHip, body.midShoulder, body.midAnkle) / body.torso;
  const lineScore = mapRange(Math.abs(hipOffset), 0.22, 0.04);
  const symmetryScore = mapRange(diff, 30, 8);

  const faults: FormFault[] = [];
  if (load > 25) {
    if (elbow > 115) {
      faults.push({ key: '下放不充分', severity: clamp((elbow - 115) / 30, 0, 1) });
    }
    if (hipOffset > 0.12) {
      faults.push({ key: '核心下塌', severity: clamp((hipOffset - 0.12) / 0.15, 0, 1) });
    } else if (hipOffset < -0.12) {
      faults.push({ key: '臀部过高', severity: clamp((-hipOffset - 0.12) / 0.15, 0, 1) });
    }
    if (diff > 18) {
      faults.push({ key: '左右不对称', severity: clamp((diff - 18) / 20, 0, 1) });
    }
    if (bodyLine != null && bodyLine < 150) {
      faults.push({ key: '身体未成直线', severity: clamp((150 - bodyLine) / 30, 0, 1) });
    }
  }

  const score = weightedScore([
    [depthScore, 0.4],
    [lineScore, 0.4],
    [symmetryScore, 0.2],
  ]);

  return createMeasureResult(
    body,
    {
      load,
      score,
      faults,
      primaryAngle: elbow,
      metrics: {
        left_elbow: left,
        right_elbow: right,
        body_line: bodyLine,
        hip_offset: hipOffset,
      },
    },
    indices,
  );
};

const measureJumpingJack = (body: BodyFrame): MeasureResult => {
  const at = body.at;
  const wristMid = midpoint(at(LEFT_WRIST), at(RIGHT_WRIST));
  const ankleSpread = distance(at(LEFT_ANKLE), at(RIGHT_ANKLE));
  const indices = [
    LEFT_SHOULDER,
    RIGHT_SHOULDER,
    LEFT_WRIST,
    RIGHT_WRIST,
    LEFT_HIP,
    RIGHT_HIP,
    LEFT_ANKLE,
    RIGHT_ANKLE,
  ];

  if (!isVisible(at(LEFT_WRIST)) || !isVisible(at(RIGHT_WRIST))) {
    return createMeasureResult(
      body,
      {
        load: 0,
        score: 0,
        faults: [{ key: '关键点不可见', severity: 1 }],
        primaryAngle: null,
        metrics: {},
      },
      indices,
    );
  }

  const armElevation = (body.midShoulder.y - wristMid.y) / body.torso;
  const legRatio = ankleSpread / Math.max(body.shoulderWidth, body.hipWidth, 0.05);
  // Overhead means the wrists clear the head, not merely the shoulders.
  const head = at(NOSE);
  const headClearance = isVisible(head) ? (head.y - wristMid.y) / body.torso : null;
  const overheadScore = headClearance == null ? 100 : mapRange(headClearance, -0.2, 0.25);
  const armScore = weightedScore([
    [mapRange(armElevation, -0.1, 0.9), 0.8],
    [overheadScore, 0.2],
  ]);
  const legScore = mapRange(legRatio, 0.9, 2.2);
  const armSymmetry = Math.abs(at(LEFT_WRIST).y - at(RIGHT_WRIST).y) / body.torso;
  const symmetryScore = mapRange(armSymmetry, 0.3, 0.05);
  const bodyLine = angleDeg(body.midShoulder, body.midHip, body.midAnkle);
  const extensionScore = bodyLine == null ? 60 : mapRange(bodyLine, 150, 172);

  const armLoad = mapRange(armElevation, -0.8, 0.9);
  const legLoad = mapRange(legRatio, 1.0, 2.3);
  const load = clamp(armLoad * 0.65 + legLoad * 0.35);

  const faults: FormFault[] = [];
  if (load > 25) {
    if (armScore < 60) {
      faults.push({ key: '手臂抬起不足', severity: clamp((60 - armScore) / 60, 0, 1) });
    }
    if (legScore < 55) {
      faults.push({ key: '双腿张开不足', severity: clamp((55 - legScore) / 55, 0, 1) });
    }
    if (symmetryScore < 60) {
      faults.push({ key: '左右不对称', severity: clamp((60 - symmetryScore) / 60, 0, 1) });
    }
  }

  const score = weightedScore([
    [armScore, 0.4],
    [legScore, 0.3],
    [symmetryScore, 0.15],
    [extensionScore, 0.15],
  ]);

  return createMeasureResult(
    body,
    {
      load,
      score,
      faults,
      primaryAngle: armElevation,
      metrics: {
        arm_elevation: armElevation,
        leg_ratio: legRatio,
        body_line: bodyLine,
      },
    },
    indices,
  );
};

const measurePlank = (body: BodyFrame, stabilityScore: number): MeasureResult => {
  const at = body.at;
  const bodyLine = angleDeg(body.midShoulder, body.midHip, body.midAnkle);
  const leftElbow = angleDeg(at(LEFT_SHOULDER), at(LEFT_ELBOW), at(LEFT_WRIST));
  const rightElbow = angleDeg(at(RIGHT_SHOULDER), at(RIGHT_ELBOW), at(RIGHT_WRIST));
  const { value: elbow } = combineSideAngles(leftElbow, rightElbow);
  const indices = [
    LEFT_SHOULDER,
    RIGHT_SHOULDER,
    LEFT_ELBOW,
    RIGHT_ELBOW,
    LEFT_WRIST,
    RIGHT_WRIST,
    LEFT_HIP,
    RIGHT_HIP,
    LEFT_ANKLE,
    RIGHT_ANKLE,
  ];

  if (bodyLine == null) {
    return createMeasureResult(
      body,
      {
        load: 0,
        score: 0,
        faults: [{ key: '关键点不可见', severity: 1 }],
        primaryAngle: null,
        metrics: {},
      },
      indices,
    );
  }

  const lineScore = mapRange(bodyLine, 150, 173);
  const elbowScore = elbow == null ? 50 : mapRange(Math.abs(elbow - 95), 45, 5);
  // A forearm plank stacks the elbow under the shoulder; the wrist points forward.
  const elbowMidX = (at(LEFT_ELBOW).x + at(RIGHT_ELBOW).x) / 2;
  const elbowOffset = Math.abs(elbowMidX - body.midShoulder.x) / body.torso;
  const alignmentScore = mapRange(elbowOffset, 0.45, 0.08);
  const hipOffset = verticalOffsetFromLine(body.midHip, body.midShoulder, body.midAnkle) / body.torso;

  const faults: FormFault[] = [];
  if (hipOffset > 0.12) {
    faults.push({ key: '骨盆下沉', severity: clamp((hipOffset - 0.12) / 0.15, 0, 1) });
  } else if (hipOffset < -0.12) {
    faults.push({ key: '臀部过高', severity: clamp((-hipOffset - 0.12) / 0.15, 0, 1) });
  }
  if (alignmentScore < 60) {
    faults.push({ key: '肘部未对齐', severity: clamp((60 - alignmentScore) / 60, 0, 1) });
  }
  if (stabilityScore < 65) {
    faults.push({ key: '身体晃动', severity: clamp((65 - stabilityScore) / 65, 0, 1) });
  }

  const score = weightedScore([
    [lineScore, 0.45],
    [elbowScore, 0.18],
    [alignmentScore, 0.17],
    [stabilityScore, 0.2],
  ]);

  return createMeasureResult(
    body,
    {
      load: score,
      score,
      faults,
      primaryAngle: bodyLine,
      metrics: {
        body_line: bodyLine,
        elbow,
        elbow_offset: elbowOffset,
        hip_offset: hipOffset,
        stability: stabilityScore,
      },
    },
    indices,
  );
};

interface RepConfig {
  downEnter: number;
  upEnter: number;
  minDwellMs: number;
  minRepMs: number;
  minLoadRange: number;
  minConfidence: number;
}

const SQUAT_CONFIG: RepConfig = {
  downEnter: 70,
  upEnter: 25,
  minDwellMs: 120,
  minRepMs: 450,
  minLoadRange: 50,
  minConfidence: 0.45,
};

const PUSHUP_CONFIG: RepConfig = {
  downEnter: 70,
  upEnter: 25,
  minDwellMs: 120,
  minRepMs: 400,
  minLoadRange: 50,
  minConfidence: 0.45,
};

const JUMPING_JACK_CONFIG: RepConfig = {
  downEnter: 70,
  upEnter: 30,
  minDwellMs: 100,
  minRepMs: 260,
  minLoadRange: 50,
  minConfidence: 0.4,
};

const hasRequiredLandmarks = (landmarks: Landmark[]) =>
  Array.isArray(landmarks) && landmarks.length > RIGHT_ANKLE;

const emptyFrame = (): AnalysisFrame => ({
  phase: 'up',
  progress: 0,
  formScore: 0,
  repCompleted: false,
  repScore: 0,
  enteredDown: false,
  enteredUp: false,
  faults: [],
  confidence: 0,
  view: 'unknown',
  primaryAngle: null,
  isHolding: false,
  holdSeconds: 0,
});

class RepAnalyzer implements ExerciseAnalyzer {
  private config: RepConfig;
  private measure: (body: BodyFrame) => MeasureResult;
  private phase: 'up' | 'down' = 'up';
  private candidate: 'up' | 'down' | null = null;
  private candidateSince = 0;
  private repStartedAt = 0;
  private repMinLoad = 0;
  private repMaxLoad = 0;
  private bottomLoad = -1;
  private bottomScore = 0;
  private formScore = 0;

  constructor(config: RepConfig, measure: (body: BodyFrame) => MeasureResult) {
    this.config = config;
    this.measure = measure;
  }

  reset() {
    this.phase = 'up';
    this.candidate = null;
    this.candidateSince = 0;
    this.repStartedAt = 0;
    this.repMinLoad = 0;
    this.repMaxLoad = 0;
    this.bottomLoad = -1;
    this.bottomScore = 0;
    this.formScore = 0;
  }

  update(landmarks: Landmark[], timestamp: number, aspectRatio?: number): AnalysisFrame {
    if (!hasRequiredLandmarks(landmarks)) {
      const frame = emptyFrame();
      frame.phase = this.phase;
      frame.formScore = this.formScore;
      frame.faults = [{ key: '关键点不可见', severity: 1 }];
      return frame;
    }

    const body = buildBody(landmarks, aspectRatio);
    const result = this.measure(body);
    const frame = emptyFrame();
    frame.view = result.view;
    frame.confidence = result.confidence;
    frame.primaryAngle = result.primaryAngle;
    frame.progress = Math.round(result.load);

    if (result.confidence < this.config.minConfidence) {
      this.candidate = null;
      // Abort an in-flight rep: otherwise the person leaving the frame and
      // returning would be counted as one long, valid repetition.
      if (this.phase === 'down') {
        this.phase = 'up';
        this.repStartedAt = timestamp;
        this.repMinLoad = 0;
        this.repMaxLoad = 0;
        this.bottomLoad = -1;
        this.bottomScore = 0;
      }
      frame.faults = [{ key: '关键点不可见', severity: 1 }];
      frame.formScore = this.formScore;
      frame.phase = this.phase;
      return frame;
    }

    const active = result.load >= 25 || this.phase === 'down';
    if (active) {
      const instant = clamp(result.score);
      this.formScore =
        this.formScore <= 0 ? instant : this.formScore + (instant - this.formScore) * 0.3;
      if (result.load > this.bottomLoad) {
        this.bottomLoad = result.load;
        this.bottomScore = instant;
      }
    }
    frame.formScore = this.formScore;
    frame.faults = active ? result.faults : [];

    this.repMinLoad = Math.min(this.repMinLoad, result.load);
    this.repMaxLoad = Math.max(this.repMaxLoad, result.load);

    const target =
      this.phase === 'up'
        ? result.load >= this.config.downEnter
          ? 'down'
          : null
        : result.load <= this.config.upEnter
          ? 'up'
          : null;

    if (target) {
      if (this.candidate !== target) {
        this.candidate = target;
        this.candidateSince = timestamp;
      }
      if (timestamp - this.candidateSince >= this.config.minDwellMs) {
        const previous = this.phase;
        this.phase = target;
        this.candidate = null;

        if (target === 'down') {
          frame.enteredDown = true;
          this.bottomLoad = result.load;
          this.bottomScore = result.score;
        } else {
          frame.enteredUp = true;
          const range = this.repMaxLoad - this.repMinLoad;
          const duration = timestamp - this.repStartedAt;
          if (
            previous === 'down' &&
            range >= this.config.minLoadRange &&
            duration >= this.config.minRepMs
          ) {
            frame.repCompleted = true;
            frame.repScore = Math.round(this.bottomScore);
          }
          this.repStartedAt = timestamp;
          this.repMinLoad = result.load;
          this.repMaxLoad = result.load;
          this.bottomLoad = -1;
        }
      }
    } else {
      this.candidate = null;
    }

    frame.phase = this.phase;
    return frame;
  }
}

class PlankAnalyzer implements ExerciseAnalyzer {
  private formScore = 0;
  private holding = false;
  private holdStart = 0;
  private lineHistory: number[] = [];

  reset() {
    this.formScore = 0;
    this.holding = false;
    this.holdStart = 0;
    this.lineHistory = [];
  }

  private stabilityScore() {
    if (this.lineHistory.length < 4) return 100;
    let totalChange = 0;
    for (let i = 1; i < this.lineHistory.length; i += 1) {
      const current = this.lineHistory[i];
      const previous = this.lineHistory[i - 1];
      if (current == null || previous == null) continue;
      totalChange += Math.abs(current - previous);
    }
    const averageChange = totalChange / (this.lineHistory.length - 1);
    return mapRange(averageChange, 7, 0.5);
  }

  update(landmarks: Landmark[], timestamp: number, aspectRatio?: number): AnalysisFrame {
    if (!hasRequiredLandmarks(landmarks)) {
      const frame = emptyFrame();
      frame.phase = 'holding';
      frame.formScore = this.formScore;
      frame.faults = [{ key: '关键点不可见', severity: 1 }];
      return frame;
    }

    const body = buildBody(landmarks, aspectRatio);
    const stability = this.stabilityScore();
    const result = measurePlank(body, stability);
    const frame = emptyFrame();
    frame.phase = 'holding';
    frame.view = result.view === 'unknown' ? 'side' : result.view;
    frame.confidence = result.confidence;
    frame.primaryAngle = result.primaryAngle;
    frame.progress = Math.round(result.score);

    const bodyLine = result.metrics.body_line;
    if (typeof bodyLine === 'number') {
      this.lineHistory.push(bodyLine);
      if (this.lineHistory.length > 30) this.lineHistory.shift();
    }

    if (result.confidence < 0.4) {
      this.holding = false;
      this.holdStart = 0;
      frame.faults = [{ key: '关键点不可见', severity: 1 }];
      frame.formScore = this.formScore;
      return frame;
    }

    const instant = clamp(result.score);
    this.formScore = this.formScore <= 0 ? instant : this.formScore + (instant - this.formScore) * 0.25;
    frame.formScore = this.formScore;
    frame.faults = result.faults;

    const shouldHold = this.holding
      ? this.formScore >= 70
      : this.formScore >= 82 && typeof bodyLine === 'number';
    if (shouldHold && !this.holding) {
      this.holding = true;
      this.holdStart = timestamp;
    } else if (!shouldHold) {
      this.holding = false;
      this.holdStart = 0;
    }

    frame.isHolding = this.holding;
    frame.holdSeconds = this.holding ? Math.max(0, (timestamp - this.holdStart) / 1000) : 0;
    return frame;
  }
}

export function createExerciseAnalyzer(mode: ExerciseMode): ExerciseAnalyzer {
  switch (mode) {
    case 'pushup':
      return new RepAnalyzer(PUSHUP_CONFIG, measurePushup);
    case 'jumping_jack':
      return new RepAnalyzer(JUMPING_JACK_CONFIG, measureJumpingJack);
    case 'plank':
      return new PlankAnalyzer();
    case 'squat':
    default:
      return new RepAnalyzer(SQUAT_CONFIG, measureSquat);
  }
}
