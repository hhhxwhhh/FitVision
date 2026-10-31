import { describe, expect, it } from 'vitest';
import {
  createExerciseAnalyzer,
  type ExerciseMode,
  type Landmark,
} from './poseRecognition';

const ASPECT = 16 / 9;

const pose = (
  points: Record<number, { x: number; y: number }>,
  visibility = 0.95,
): Landmark[] => {
  const landmarks: Landmark[] = Array.from({ length: 33 }, () => ({
    x: 0.5,
    y: 0.5,
    z: 0,
    visibility,
  }));
  for (const [index, point] of Object.entries(points)) {
    const slot = landmarks[Number(index)];
    if (slot) {
      slot.x = point.x;
      slot.y = point.y;
    }
  }
  return landmarks;
};

const frontStanding = () =>
  pose({
    0: { x: 0.5, y: 0.2 },
    11: { x: 0.4, y: 0.3 },
    12: { x: 0.6, y: 0.3 },
    13: { x: 0.34, y: 0.45 },
    14: { x: 0.66, y: 0.45 },
    15: { x: 0.3, y: 0.58 },
    16: { x: 0.7, y: 0.58 },
    23: { x: 0.44, y: 0.55 },
    24: { x: 0.56, y: 0.55 },
    25: { x: 0.42, y: 0.75 },
    26: { x: 0.58, y: 0.75 },
    27: { x: 0.42, y: 0.95 },
    28: { x: 0.58, y: 0.95 },
  });

const frontSquat = (kneeX: number) => {
  const inner = 0.5 - kneeX;
  return pose({
    0: { x: 0.5, y: 0.2 },
    11: { x: 0.4, y: 0.3 },
    12: { x: 0.6, y: 0.3 },
    13: { x: 0.34, y: 0.45 },
    14: { x: 0.66, y: 0.45 },
    15: { x: 0.3, y: 0.58 },
    16: { x: 0.7, y: 0.58 },
    23: { x: 0.44, y: 0.55 },
    24: { x: 0.56, y: 0.55 },
    25: { x: kneeX, y: 0.72 },
    26: { x: 0.5 + inner, y: 0.72 },
    27: { x: 0.42, y: 0.95 },
    28: { x: 0.58, y: 0.95 },
  });
};

const sideStanding = () =>
  pose({
    0: { x: 0.5, y: 0.2 },
    11: { x: 0.49, y: 0.3 },
    12: { x: 0.51, y: 0.3 },
    13: { x: 0.49, y: 0.45 },
    14: { x: 0.51, y: 0.45 },
    15: { x: 0.49, y: 0.6 },
    16: { x: 0.51, y: 0.6 },
    23: { x: 0.49, y: 0.5 },
    24: { x: 0.51, y: 0.5 },
    25: { x: 0.49, y: 0.66 },
    26: { x: 0.51, y: 0.66 },
    27: { x: 0.49, y: 0.82 },
    28: { x: 0.51, y: 0.82 },
  });

const sideSquat = () =>
  pose({
    0: { x: 0.5, y: 0.2 },
    11: { x: 0.49, y: 0.3 },
    12: { x: 0.51, y: 0.3 },
    13: { x: 0.49, y: 0.45 },
    14: { x: 0.51, y: 0.45 },
    15: { x: 0.49, y: 0.6 },
    16: { x: 0.51, y: 0.6 },
    23: { x: 0.49, y: 0.5 },
    24: { x: 0.51, y: 0.5 },
    25: { x: 0.61, y: 0.66 },
    26: { x: 0.63, y: 0.66 },
    27: { x: 0.49, y: 0.82 },
    28: { x: 0.51, y: 0.82 },
  });

const pushup = (down: boolean) =>
  pose(
    down
      ? {
          0: { x: 0.1, y: 0.48 },
          11: { x: 0.24, y: 0.5 },
          12: { x: 0.26, y: 0.5 },
          13: { x: 0.24, y: 0.65 },
          14: { x: 0.26, y: 0.65 },
          15: { x: 0.4, y: 0.65 },
          16: { x: 0.4, y: 0.65 },
          23: { x: 0.49, y: 0.5 },
          24: { x: 0.51, y: 0.5 },
          25: { x: 0.49, y: 0.5 },
          26: { x: 0.51, y: 0.5 },
          27: { x: 0.74, y: 0.5 },
          28: { x: 0.76, y: 0.5 },
        }
      : {
          0: { x: 0.1, y: 0.48 },
          11: { x: 0.24, y: 0.5 },
          12: { x: 0.26, y: 0.5 },
          13: { x: 0.24, y: 0.65 },
          14: { x: 0.26, y: 0.65 },
          15: { x: 0.24, y: 0.8 },
          16: { x: 0.26, y: 0.8 },
          23: { x: 0.49, y: 0.5 },
          24: { x: 0.51, y: 0.5 },
          25: { x: 0.49, y: 0.5 },
          26: { x: 0.51, y: 0.5 },
          27: { x: 0.74, y: 0.5 },
          28: { x: 0.76, y: 0.5 },
        },
  );

const jumpingJack = (open: boolean) =>
  pose(
    open
      ? {
          0: { x: 0.5, y: 0.2 },
          11: { x: 0.4, y: 0.3 },
          12: { x: 0.6, y: 0.3 },
          13: { x: 0.32, y: 0.2 },
          14: { x: 0.68, y: 0.2 },
          15: { x: 0.25, y: 0.12 },
          16: { x: 0.75, y: 0.12 },
          23: { x: 0.44, y: 0.55 },
          24: { x: 0.56, y: 0.55 },
          25: { x: 0.35, y: 0.75 },
          26: { x: 0.65, y: 0.75 },
          27: { x: 0.25, y: 0.95 },
          28: { x: 0.75, y: 0.95 },
        }
      : {
          0: { x: 0.5, y: 0.2 },
          11: { x: 0.4, y: 0.3 },
          12: { x: 0.6, y: 0.3 },
          13: { x: 0.38, y: 0.42 },
          14: { x: 0.62, y: 0.42 },
          15: { x: 0.4, y: 0.55 },
          16: { x: 0.6, y: 0.55 },
          23: { x: 0.44, y: 0.55 },
          24: { x: 0.56, y: 0.55 },
          25: { x: 0.44, y: 0.75 },
          26: { x: 0.56, y: 0.75 },
          27: { x: 0.45, y: 0.95 },
          28: { x: 0.55, y: 0.95 },
        },
  );

const plankPose = () =>
  pose({
    0: { x: 0.1, y: 0.48 },
    11: { x: 0.24, y: 0.5 },
    12: { x: 0.26, y: 0.5 },
    13: { x: 0.24, y: 0.62 },
    14: { x: 0.26, y: 0.62 },
    15: { x: 0.4, y: 0.62 },
    16: { x: 0.4, y: 0.62 },
    23: { x: 0.49, y: 0.5 },
    24: { x: 0.51, y: 0.5 },
    25: { x: 0.49, y: 0.5 },
    26: { x: 0.51, y: 0.5 },
    27: { x: 0.74, y: 0.5 },
    28: { x: 0.76, y: 0.5 },
  });

const analyze = (mode: ExerciseMode, frames: Array<[Landmark[], number]>) => {
  const analyzer = createExerciseAnalyzer(mode);
  return frames.map(([landmarks, timestamp]) =>
    analyzer.update(landmarks, timestamp, ASPECT),
  );
};

describe('view detection and confidence gating', () => {
  it('recognises a front view and a side view', () => {
    const front = createExerciseAnalyzer('squat').update(frontStanding(), 0, ASPECT);
    const side = createExerciseAnalyzer('squat').update(sideSquat(), 0, ASPECT);
    expect(front.view).toBe('front');
    expect(side.view).toBe('side');
    expect(front.confidence).toBeGreaterThan(0.8);
  });

  it('rejects a skeleton whose landmarks are barely visible', () => {
    const analyzer = createExerciseAnalyzer('squat');
    const frame = analyzer.update(frontSquat(0.3).map((point) => ({ ...point, visibility: 0.1 })), 0, ASPECT);
    expect(frame.confidence).toBeLessThan(0.45);
    expect(frame.faults.map((fault) => fault.key)).toContain('关键点不可见');
    expect(frame.repCompleted).toBe(false);
  });

  it('handles a short landmark array without throwing', () => {
    const analyzer = createExerciseAnalyzer('pushup');
    const frame = analyzer.update([{ x: 0.5, y: 0.5, z: 0 }], 0, ASPECT);
    expect(frame.faults.map((fault) => fault.key)).toContain('关键点不可见');
  });
});

describe('squat analysis', () => {
  it('flags a shallow squat and reports a lower score', () => {
    const shallow = createExerciseAnalyzer('squat').update(frontSquat(0.38), 0, ASPECT);
    const deep = createExerciseAnalyzer('squat').update(frontSquat(0.3), 0, ASPECT);

    expect(shallow.faults.map((fault) => fault.key)).toContain('下蹲深度不足');
    expect(deep.progress).toBeGreaterThan(shallow.progress);
    expect(deep.formScore).toBeGreaterThan(shallow.formScore);
  });

  it('counts a full down-up cycle only after the minimum duration', () => {
    const open = frontSquat(0.3);
    const closed = frontStanding();

    const quick = analyze('squat', [
      [closed, 0],
      [open, 150],
      [open, 300],
      [closed, 400],
      [closed, 500],
    ]);
    expect(quick.some((frame) => frame.repCompleted)).toBe(false);

    const full = analyze('squat', [
      [closed, 0],
      [open, 150],
      [open, 300],
      [closed, 400],
      [closed, 500],
      [closed, 600],
    ]);
    const completed = full.filter((frame) => frame.repCompleted);
    expect(completed).toHaveLength(1);
    expect(completed[0]?.repScore).toBeGreaterThan(70);
  });

  it('aborts an in-flight rep when tracking is lost, then recovers', () => {
    const closed = frontStanding();
    const open = frontSquat(0.3);
    const hidden = open.map((point) => ({ ...point, visibility: 0.1 }));
    const frames = analyze('squat', [
      [closed, 0],
      [open, 150],
      [open, 300],
      [hidden, 350],
      [closed, 400],
      [closed, 500],
      [closed, 600],
    ]);
    expect(frames.some((frame) => frame.repCompleted)).toBe(false);

    const recovered = analyze('squat', [
      [closed, 0],
      [open, 150],
      [open, 300],
      [hidden, 350],
      [closed, 400],
      [open, 700],
      [open, 850],
      [closed, 900],
      [closed, 1000],
      [closed, 1100],
    ]);
    expect(recovered.filter((frame) => frame.repCompleted)).toHaveLength(1);
  });

  it('does not count a rep faster than the minimum duration', () => {
    const open = sideSquat();
    const closed = sideStanding();
    const frames = analyze('squat', [
      [closed, 0],
      [open, 40],
      [open, 160],
      [closed, 200],
      [closed, 260],
      [closed, 320],
    ]);
    expect(frames.some((frame) => frame.repCompleted)).toBe(false);
  });
});

describe('push-up analysis', () => {
  it('reports elbow depth and body-line alignment', () => {
    const frame = createExerciseAnalyzer('pushup').update(pushup(true), 0, ASPECT);
    expect(frame.view).toBe('side');
    expect(frame.progress).toBeGreaterThan(70);
    expect(frame.faults.map((fault) => fault.key)).not.toContain('下放不充分');
  });

  it('counts a down-up cycle', () => {
    const down = pushup(true);
    const up = pushup(false);
    const frames = analyze('pushup', [
      [up, 0],
      [down, 150],
      [down, 300],
      [up, 400],
      [up, 500],
      [up, 600],
    ]);
    expect(frames.filter((frame) => frame.repCompleted)).toHaveLength(1);
  });
});

describe('jumping jack analysis', () => {
  it('opens and closes with a full cycle', () => {
    const open = jumpingJack(true);
    const closed = jumpingJack(false);
    const frames = analyze('jumping_jack', [
      [closed, 0],
      [open, 150],
      [open, 250],
      [closed, 300],
      [closed, 400],
      [closed, 500],
    ]);
    expect(frames.filter((frame) => frame.repCompleted)).toHaveLength(1);
  });

  it('detects an open pose with raised arms', () => {
    const frame = createExerciseAnalyzer('jumping_jack').update(jumpingJack(true), 0, ASPECT);
    expect(frame.progress).toBeGreaterThan(70);
    expect(frame.faults.map((fault) => fault.key)).not.toContain('手臂抬起不足');
  });
});

describe('plank analysis', () => {
  it('accumulates hold time while the form is stable', () => {
    const analyzer = createExerciseAnalyzer('plank');
    let last = analyzer.update(plankPose(), 1000, ASPECT);
    for (let index = 1; index <= 40; index += 1) {
      last = analyzer.update(plankPose(), 1000 + index * 33, ASPECT);
    }
    expect(last.isHolding).toBe(true);
    expect(last.holdSeconds).toBeGreaterThan(0.5);
    expect(last.formScore).toBeGreaterThan(70);
  });
});
