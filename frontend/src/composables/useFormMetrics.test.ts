import { describe, expect, it } from 'vitest';
import {
  ERROR_TIP_MAP,
  FALLBACK_TIP,
  STANDARD_REP_SCORE,
  mostFrequentError,
  scoreQualityBadge,
  useFormMetrics,
} from './useFormMetrics';

describe('scoreQualityBadge', () => {
  it('labels each score band', () => {
    expect(scoreQualityBadge(95).label).toBe('优秀');
    expect(scoreQualityBadge(85).label).toBe('良好');
    expect(scoreQualityBadge(75).label).toBe('一般');
    expect(scoreQualityBadge(50).label).toBe('待改进');
  });

  it('clamps the percentage into 0-100', () => {
    expect(scoreQualityBadge(-20).percent).toBe(0);
    expect(scoreQualityBadge(140).percent).toBe(100);
  });

  it('always reports a colour', () => {
    for (const score of [0, 60, 72, 82, 91, 100]) {
      expect(scoreQualityBadge(score).color).toMatch(/^#[0-9a-f]{6}$/i);
    }
  });
});

describe('mostFrequentError', () => {
  it('returns the most frequent fault', () => {
    expect(mostFrequentError({ '膝盖内扣': 2, '下蹲深度不足': 5 })).toBe('下蹲深度不足');
  });

  it('falls back to the no-error label when empty', () => {
    expect(mostFrequentError({})).toBe('暂无明显错误');
  });
});

describe('useFormMetrics', () => {
  it('grows and breaks the standard streak', () => {
    const metrics = useFormMetrics();
    metrics.registerRep(STANDARD_REP_SCORE + 1);
    metrics.registerRep(STANDARD_REP_SCORE + 5);
    expect(metrics.standardStreak.value).toBe(2);
    expect(metrics.bestStreak.value).toBe(2);

    metrics.registerRep(40);
    expect(metrics.standardStreak.value).toBe(0);
    expect(metrics.bestStreak.value).toBe(2);
  });

  it('counts each fault once per occurrence batch', () => {
    const metrics = useFormMetrics();
    metrics.recordFaults(['膝盖内扣', '膝盖内扣', '下蹲深度不足']);
    expect(metrics.errorCounters.value['膝盖内扣']).toBe(1);
    expect(metrics.commonErrorLabel.value).toBe('膝盖内扣');
    expect(metrics.commonErrorTip.value).toBe(ERROR_TIP_MAP['膝盖内扣']);

    metrics.recordFaults(['下蹲深度不足', '下蹲深度不足']);
    expect(metrics.commonErrorLabel.value).toBe('下蹲深度不足');
  });

  it('exposes a tip for every fault the pose engine can emit', () => {
    const metrics = useFormMetrics();
    metrics.recordFaults(['上卷幅度不足']);
    expect(metrics.commonErrorTip.value).not.toBe(FALLBACK_TIP);
  });

  it('resets back to the initial state', () => {
    const metrics = useFormMetrics();
    metrics.updateQualityBadge(92);
    metrics.registerRep(90);
    metrics.recordFaults(['膝盖内扣']);

    metrics.reset();
    expect(metrics.qualityLabel.value).toBe('待评估');
    expect(metrics.standardStreak.value).toBe(0);
    expect(metrics.bestStreak.value).toBe(0);
    expect(metrics.commonErrorLabel.value).toBe('暂无明显错误');
    expect(metrics.hasErrors.value).toBe(false);
  });
});
