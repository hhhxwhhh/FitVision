"""训练容量引擎（`utils.volume`）的单元测试。

纯 Python、无 Django 依赖，可直接运行：

    cd backend && python -m unittest utils.test_volume
"""

import unittest
from datetime import date, timedelta

from utils.volume import (
    CONCENTRATION_WARN,
    MIN_TREND_WEEKS,
    MUSCLE_VOLUME_CEILING,
    MUSCLE_VOLUME_FLOOR,
    POWER_MEAN_ORDER,
    MuscleVolume,
    SessionSets,
    SetVolume,
    average_muscle_volumes,
    gini,
    muscle_volumes,
    power_mean,
    session_volume,
    theil_sen_slope,
    trend_label,
    volume_report,
    weekly_summary,
    weekly_trend,
)


class PowerMeanTests(unittest.TestCase):
    """幂平均的数学性质。"""

    def test_empty_returns_zero(self):
        self.assertEqual(power_mean([]), 0.0)

    def test_order_one_is_arithmetic_mean(self):
        self.assertAlmostEqual(power_mean([2.0, 4.0], 1.0), 3.0)

    def test_order_two_is_root_mean_square(self):
        self.assertAlmostEqual(power_mean([3.0, 4.0], 2.0), 3.5355339059327378, places=6)

    def test_order_zero_is_geometric_mean(self):
        # 几何平均 = exp(mean(ln x)) = sqrt(4) = 2
        self.assertAlmostEqual(power_mean([4.0, 1.0], 0.0), 2.0)

    def test_identical_values_are_unchanged(self):
        for value in (1.0, 7.5, 250.0):
            self.assertAlmostEqual(power_mean([value] * 4), value)

    def test_default_order_resists_outliers_more_than_arithmetic(self):
        values = [10.0] * 9 + [1000.0]
        robust = power_mean(values, POWER_MEAN_ORDER)
        arithmetic = power_mean(values, 1.0)
        self.assertLess(robust, arithmetic)

    def test_outlier_moves_robust_mean_less(self):
        base = [20.0] * 5
        with_outlier = base + [1000.0]
        robust_delta = abs(power_mean(with_outlier, 0.5) - power_mean(base, 0.5))
        arithmetic_delta = abs(power_mean(with_outlier, 1.0) - power_mean(base, 1.0))
        self.assertLess(robust_delta, arithmetic_delta)

    def test_negative_values_rejected(self):
        with self.assertRaises(ValueError):
            power_mean([-1.0, 2.0], 1.0)

    def test_geometric_mean_skips_zeros(self):
        # 含 0 时几何平均的极限式不能直接算 log，引擎选择跳过 0
        self.assertAlmostEqual(power_mean([0.0, 4.0], 0.0), 4.0)

    def test_monotonic_in_order_for_spread_data(self):
        values = [1.0, 5.0, 20.0]
        self.assertLess(power_mean(values, 0.0), power_mean(values, 1.0))
        self.assertLess(power_mean(values, 1.0), power_mean(values, 2.0))


class GiniTests(unittest.TestCase):
    """Gini 系数的边界与含义。"""

    def test_empty_is_zero(self):
        self.assertEqual(gini([]), 0.0)

    def test_single_value_is_zero(self):
        self.assertEqual(gini([42.0]), 0.0)

    def test_all_equal_is_zero(self):
        self.assertAlmostEqual(gini([10.0] * 5), 0.0, places=6)

    def test_all_zero_is_zero(self):
        self.assertEqual(gini([0.0] * 4), 0.0)

    def test_one_dominant_value_is_high(self):
        value = gini([1000.0] + [1.0] * 9)
        self.assertGreater(value, 0.8)
        self.assertLessEqual(value, 1.0)

    def test_within_bounds(self):
        value = gini([3.0, 9.0, 1.0, 22.0])
        self.assertGreaterEqual(value, 0.0)
        self.assertLessEqual(value, 1.0)

    def test_order_independent(self):
        self.assertAlmostEqual(gini([5.0, 1.0, 9.0]), gini([9.0, 5.0, 1.0]))

    def test_negative_values_ignored(self):
        self.assertAlmostEqual(gini([-5.0, 4.0, 4.0]), gini([4.0, 4.0]), places=6)

    def test_zeros_participate_as_unequal_members(self):
        # 3 个相等 + 5 个 0：离散度确实存在，不该是 0
        self.assertGreater(gini([300.0, 300.0, 300.0] + [0.0] * 5), 0.0)


class TheilSenSlopeTests(unittest.TestCase):
    """Theil–Sen 稳健斜率。"""

    def test_too_few_points_is_zero(self):
        self.assertEqual(theil_sen_slope([]), 0.0)
        self.assertEqual(theil_sen_slope([5.0]), 0.0)

    def test_perfect_line(self):
        self.assertAlmostEqual(theil_sen_slope([1.0, 3.0, 5.0, 7.0]), 2.0)

    def test_flat_series(self):
        self.assertAlmostEqual(theil_sen_slope([4.0] * 6), 0.0)

    def test_outlier_does_not_flip_sign(self):
        base = [10.0, 11.0, 12.0, 13.0]
        noisy = base + [400.0]
        self.assertGreater(theil_sen_slope(noisy), 0.0)

    def test_outlier_does_not_flip_negative_trend(self):
        base = [40.0, 38.0, 36.0, 34.0]
        noisy = base + [0.5]
        self.assertLess(theil_sen_slope(noisy), 0.0)

    def test_median_of_pairwise_slopes(self):
        # 斜率集合：1, 3, 2 → 中位数 2
        self.assertAlmostEqual(theil_sen_slope([0.0, 1.0, 4.0]), 2.0)

    def test_large_sample_outlier_keeps_trend_magnitude(self):
        # n=8 时才真正体现稳健性：斜率应接近干净序列的斜率
        clean = [100.0, 110.0, 120.0, 130.0, 140.0, 150.0, 160.0, 170.0]
        noisy = clean[:-1] + [9000.0]
        self.assertAlmostEqual(theil_sen_slope(noisy), theil_sen_slope(clean), places=6)


class SetVolumeTests(unittest.TestCase):
    """单组容量的换算。"""

    def test_tonnage(self):
        self.assertAlmostEqual(SetVolume(reps=10, weight=60.0).tonnage, 600.0)

    def test_measurable_requires_weight(self):
        self.assertFalse(SetVolume(reps=10, weight=0.0).is_measurable)
        self.assertTrue(SetVolume(reps=10, weight=60.0).is_measurable)

    def test_measurable_requires_reps(self):
        self.assertFalse(SetVolume(reps=0, weight=60.0).is_measurable)

    def test_intensity_volume_scales_with_percent(self):
        light = SetVolume(reps=10, weight=100.0, percent=50.0)
        heavy = SetVolume(reps=10, weight=100.0, percent=90.0)
        self.assertAlmostEqual(light.intensity_volume, 500.0)
        self.assertAlmostEqual(heavy.intensity_volume, 900.0)

    def test_intensity_volume_zero_without_measurable_data(self):
        item = SetVolume(reps=10, weight=0.0)
        self.assertEqual(item.intensity_volume, 0.0)

    def test_intensity_volume_derives_percent_from_weight_and_e1rm(self):
        item = SetVolume(reps=5, weight=100.0, e1rm=100.0)
        self.assertGreater(item.intensity_volume, 0.0)

    def test_rpe_used_when_percent_missing(self):
        item = SetVolume(reps=10, weight=50.0, rpe=8.0)
        self.assertGreater(item.intensity_volume, 0.0)


class SessionVolumeTests(unittest.TestCase):
    """单次训练的容量聚合。"""

    def test_empty_session(self):
        result = session_volume([])
        self.assertEqual(result.sets, 0)
        self.assertEqual(result.effective_volume, 0.0)
        self.assertEqual(result.tonnage, 0.0)

    def test_totals(self):
        sets = [
            SetVolume(reps=10, weight=60.0, percent=70.0),
            SetVolume(reps=10, weight=60.0, percent=70.0),
        ]
        result = session_volume(sets, day=date(2026, 3, 1))
        self.assertEqual(result.sets, 2)
        self.assertEqual(result.measurable_sets, 2)
        self.assertAlmostEqual(result.tonnage, 1200.0)
        self.assertAlmostEqual(result.intensity_volume, 840.0)

    def test_bodyweight_sets_counted_but_not_intensity_weighted(self):
        sets = [
            SetVolume(reps=20, weight=0.0),
            SetVolume(reps=10, weight=60.0, percent=70.0),
        ]
        result = session_volume(sets)
        self.assertEqual(result.sets, 2)
        self.assertEqual(result.measurable_sets, 1)

    def test_effective_volume_never_exceeds_arithmetic_sum(self):
        sets = [
            SetVolume(reps=10, weight=50.0, percent=60.0),
            SetVolume(reps=10, weight=50.0, percent=60.0),
            SetVolume(reps=1, weight=900.0, percent=100.0),
        ]
        result = session_volume(sets)
        self.assertLessEqual(result.effective_volume, result.intensity_volume)

    def test_extreme_set_marginal_contribution_is_capped(self):
        """极端组的边际贡献不超过它自己的原始强度加权容量。"""
        normal = [SetVolume(reps=10, weight=50.0, percent=60.0) for _ in range(5)]
        outlier = SetVolume(reps=1, weight=2000.0, percent=100.0)
        before = session_volume(normal).effective_volume
        after = session_volume(normal + [outlier]).effective_volume
        self.assertLessEqual(after - before, outlier.intensity_volume)
        # 而算术口径下它会全额计入
        arithmetic_before = session_volume(normal).intensity_volume
        arithmetic_after = session_volume(normal + [outlier]).intensity_volume
        self.assertAlmostEqual(arithmetic_after - arithmetic_before, outlier.intensity_volume)

    def test_date_preserved(self):
        result = session_volume([], day=date(2026, 3, 5))
        self.assertEqual(result.date, date(2026, 3, 5))

    def test_as_dict_shape(self):
        result = session_volume(
            [SetVolume(reps=10, weight=50.0, percent=70.0)], day=date(2026, 3, 1)
        )
        payload = result.as_dict()
        for key in ("date", "sets", "measurable_sets", "tonnage", "effective_volume"):
            self.assertIn(key, payload)
        self.assertEqual(payload["date"], "2026-03-01")

    def test_session_sets_volume_helper(self):
        session = SessionSets(date=date(2026, 3, 1), sets=(SetVolume(reps=10, weight=50.0, percent=70.0),))
        self.assertEqual(session.volume().sets, 1)


class MuscleVolumeTests(unittest.TestCase):
    """肌群维度的容量结构。"""

    def test_grouped_by_muscle(self):
        sets = [
            SetVolume(reps=10, weight=60.0, percent=70.0, muscle="chest"),
            SetVolume(reps=10, weight=80.0, percent=70.0, muscle="back"),
            SetVolume(reps=10, weight=60.0, percent=70.0, muscle="chest"),
        ]
        result = muscle_volumes(sets)
        by_key = {item.muscle: item for item in result}
        self.assertEqual(by_key["chest"].sets, 2)
        self.assertEqual(by_key["back"].sets, 1)
        self.assertEqual(by_key["chest"].label, "胸部")

    def test_sorted_by_effective_volume_desc(self):
        sets = [
            SetVolume(reps=10, weight=20.0, percent=70.0, muscle="chest"),
            SetVolume(reps=10, weight=120.0, percent=70.0, muscle="back"),
        ]
        result = muscle_volumes(sets)
        self.assertEqual(result[0].muscle, "back")

    def test_unknown_muscle_falls_back_to_full_body(self):
        sets = [SetVolume(reps=10, weight=60.0, percent=70.0, muscle="calves")]
        result = muscle_volumes(sets)
        self.assertEqual(result[0].muscle, "full_body")

    def test_missing_muscle_falls_back_to_full_body(self):
        sets = [SetVolume(reps=10, weight=60.0, percent=70.0, muscle=None)]
        result = muscle_volumes(sets)
        self.assertEqual(result[0].muscle, "full_body")

    def test_status_low_when_below_floor(self):
        item = MuscleVolume("chest", "胸部", 1, 100.0, 50.0, MUSCLE_VOLUME_FLOOR - 1)
        self.assertEqual(item.status(100000.0), "low")

    def test_status_high_when_above_ceiling(self):
        item = MuscleVolume("chest", "胸部", 40, 100000.0, 90000.0, MUSCLE_VOLUME_CEILING + 1)
        self.assertEqual(item.status(100000.0), "high")

    def test_status_ok_inside_band(self):
        item = MuscleVolume("chest", "胸部", 12, 10000.0, 7000.0, 7000.0)
        self.assertEqual(item.status(100000.0), "ok")

    def test_status_unknown_without_total(self):
        item = MuscleVolume("chest", "胸部", 1, 10.0, 5.0, 5.0)
        self.assertEqual(item.status(0.0), "unknown")

    def test_as_dict_share_sums_to_one(self):
        sets = [
            SetVolume(reps=10, weight=60.0, percent=70.0, muscle="chest"),
            SetVolume(reps=10, weight=60.0, percent=70.0, muscle="back"),
        ]
        muscles = muscle_volumes(sets)
        total = sum(item.effective_volume for item in muscles)
        payload = [item.as_dict(total) for item in muscles]
        self.assertAlmostEqual(sum(item["share"] for item in payload), 1.0, places=3)


class AverageMuscleVolumeTests(unittest.TestCase):
    """按周平均的肌群容量。"""

    def test_empty(self):
        self.assertEqual(average_muscle_volumes([]), ())

    def test_same_week_counted_once(self):
        sessions = [
            SessionSets(
                date=date(2026, 3, 2),
                sets=(SetVolume(reps=10, weight=60.0, percent=70.0, muscle="chest"),),
            ),
            SessionSets(
                date=date(2026, 3, 4),
                sets=(SetVolume(reps=10, weight=60.0, percent=70.0, muscle="chest"),),
            ),
        ]
        result = average_muscle_volumes(sessions)
        self.assertEqual(len(result), 1)
        self.assertEqual(result[0].weeks, 1)
        self.assertEqual(result[0].sets, 2)

    def test_two_weeks_averaged(self):
        sessions = [
            SessionSets(
                date=date(2026, 3, 2),
                sets=(SetVolume(reps=10, weight=60.0, percent=70.0, muscle="chest"),),
            ),
            SessionSets(
                date=date(2026, 3, 9),
                sets=(SetVolume(reps=10, weight=60.0, percent=70.0, muscle="chest"),),
            ),
        ]
        result = average_muscle_volumes(sessions)
        self.assertEqual(result[0].weeks, 2)
        self.assertEqual(result[0].sets, 1)  # 2 组 / 2 周

    def test_sessions_without_date_ignored(self):
        sessions = [
            SessionSets(
                date=None,
                sets=(SetVolume(reps=10, weight=60.0, percent=70.0, muscle="chest"),),
            )
        ]
        self.assertEqual(average_muscle_volumes(sessions), ())


class WeeklySummaryTests(unittest.TestCase):
    """周汇总。"""

    def _sessions(self):
        day = date(2026, 3, 2)  # 周一
        return [
            session_volume([SetVolume(reps=10, weight=60.0, percent=70.0)], day=day),
            session_volume(
                [SetVolume(reps=10, weight=60.0, percent=70.0)], day=day + timedelta(days=2)
            ),
        ]

    def test_same_week_merged(self):
        result = weekly_summary(self._sessions(), weeks=4)
        self.assertEqual(len(result), 1)
        self.assertEqual(result[0]["sessions"], 2)
        self.assertEqual(result[0]["sets"], 2)

    def test_iso_week_fields(self):
        result = weekly_summary(self._sessions(), weeks=4)
        self.assertEqual(result[0]["year"], 2026)
        self.assertEqual(result[0]["week"], 10)

    def test_keeps_only_recent_weeks(self):
        sessions = []
        for offset in range(0, 28, 7):
            day = date(2026, 1, 5) + timedelta(days=offset)
            sessions.append(
                session_volume([SetVolume(reps=10, weight=60.0, percent=70.0)], day=day)
            )
        result = weekly_summary(sessions, weeks=2)
        self.assertEqual(len(result), 2)

    def test_sessions_without_date_skipped(self):
        sessions = [session_volume([SetVolume(reps=10, weight=60.0, percent=70.0)])]
        self.assertEqual(len(weekly_summary(sessions)), 0)

    def test_ordered_earliest_first(self):
        sessions = []
        for offset in (7, 0, 14):
            day = date(2026, 1, 5) + timedelta(days=offset)
            sessions.append(
                session_volume([SetVolume(reps=10, weight=60.0, percent=70.0)], day=day)
            )
        result = weekly_summary(sessions, weeks=4)
        self.assertEqual(
            [item["week"] for item in result],
            sorted(item["week"] for item in result),
        )


class TrendTests(unittest.TestCase):
    """趋势判定。"""

    def test_label_thresholds(self):
        self.assertEqual(trend_label(0.05), "rising")
        self.assertEqual(trend_label(-0.05), "falling")
        self.assertEqual(trend_label(0.0), "steady")
        self.assertEqual(trend_label(0.01), "steady")

    def test_trend_needs_minimum_weeks(self):
        self.assertEqual(weekly_trend([]), 0.0)
        self.assertEqual(weekly_trend([{"effective_volume": 100.0}]), 0.0)

    def test_rising_trend_detected(self):
        weekly = [
            {"effective_volume": 1000.0},
            {"effective_volume": 1200.0},
            {"effective_volume": 1500.0},
            {"effective_volume": 1800.0},
        ]
        self.assertGreater(weekly_trend(weekly), 0.0)

    def test_falling_trend_detected(self):
        weekly = [
            {"effective_volume": 1800.0},
            {"effective_volume": 1500.0},
            {"effective_volume": 1200.0},
            {"effective_volume": 1000.0},
        ]
        self.assertLess(weekly_trend(weekly), 0.0)

    def test_outlier_week_does_not_flip_trend(self):
        weekly = [
            {"effective_volume": 1000.0},
            {"effective_volume": 1100.0},
            {"effective_volume": 1200.0},
            {"effective_volume": 1300.0},
            {"effective_volume": 1400.0},
            {"effective_volume": 1500.0},
            {"effective_volume": 1600.0},
            {"effective_volume": 90000.0},
        ]
        self.assertGreater(weekly_trend(weekly), 0.0)
        self.assertLess(weekly_trend(weekly), 0.2)

    def test_log_space_makes_growth_symmetric(self):
        up = weekly_trend(
            [
                {"effective_volume": 100.0},
                {"effective_volume": 133.0},
                {"effective_volume": 177.0},
                {"effective_volume": 200.0},
            ]
        )
        down = weekly_trend(
            [
                {"effective_volume": 200.0},
                {"effective_volume": 177.0},
                {"effective_volume": 133.0},
                {"effective_volume": 100.0},
            ]
        )
        self.assertAlmostEqual(abs(up), abs(down), places=6)


class VolumeReportTests(unittest.TestCase):
    """总报告。"""

    def _build(self, muscle_sets, days=(0, 3, 7, 10)):
        base = date(2026, 3, 2)
        sessions = []
        for index, day_offset in enumerate(days):
            sessions.append(
                SessionSets(
                    date=base + timedelta(days=day_offset),
                    sets=tuple(muscle_sets(index)),
                )
            )
        return sessions

    #: 覆盖 4 个 ISO 周的日期序列，足够触发趋势判定。
    SPAN_DAYS = (0, 3, 7, 10, 14, 17)

    def test_empty_report(self):
        report = volume_report([], weeks=4)
        self.assertEqual(report.verdict, "数据不足")
        self.assertEqual(report.total_effective_volume, 0.0)
        self.assertEqual(report.trend, "unknown")
        self.assertTrue(report.advice)

    def test_healthy_report(self):
        def muscles(index):
            return [
                SetVolume(reps=10, weight=60.0, percent=70.0, muscle="chest"),
                SetVolume(reps=10, weight=70.0, percent=70.0, muscle="back"),
                SetVolume(reps=10, weight=80.0, percent=70.0, muscle="legs"),
            ]

        report = volume_report(self._build(muscles), weeks=4)
        self.assertGreater(report.total_effective_volume, 0.0)
        self.assertLess(report.concentration, CONCENTRATION_WARN)
        self.assertIn(report.verdict, ("容量结构正常", "容量平稳", "容量稳步上升"))

    def test_single_muscle_counts_as_maximally_concentrated(self):
        """只练一个肌群是最极端的失衡，集中度应为 1.0。"""

        def muscles(index):
            return [SetVolume(reps=10, weight=100.0, percent=80.0, muscle="chest")]

        report = volume_report(self._build(muscles), weeks=4)
        self.assertEqual(report.concentration, 1.0)
        self.assertEqual(report.verdict, "容量结构失衡")
        self.assertTrue(any("集中" in advice or "全在" in advice for advice in report.advice))

    def test_balanced_three_muscles_not_flagged(self):
        """练胸背腿三块是正常安排，不该被判成失衡。"""

        def muscles(index):
            return [
                SetVolume(reps=10, weight=60.0, percent=70.0, muscle="chest"),
                SetVolume(reps=10, weight=60.0, percent=70.0, muscle="back"),
                SetVolume(reps=10, weight=60.0, percent=70.0, muscle="legs"),
            ]

        report = volume_report(self._build(muscles), weeks=4)
        self.assertLess(report.concentration, CONCENTRATION_WARN)
        self.assertNotEqual(report.verdict, "容量结构失衡")

    def test_two_muscles_skewed_is_flagged(self):
        def muscles(index):
            return [
                SetVolume(reps=10, weight=150.0, percent=80.0, muscle="chest"),
                SetVolume(reps=10, weight=20.0, percent=80.0, muscle="abs"),
            ]

        report = volume_report(self._build(muscles), weeks=4)
        self.assertGreater(report.concentration, CONCENTRATION_WARN)

    def test_falling_trend_verdict(self):
        # 用两个肌群，避免单肌群的"结构失衡"盖过趋势结论
        def muscles(index):
            weight = 100.0 - index * 8.0
            return [
                SetVolume(reps=10, weight=weight, percent=70.0, muscle="chest"),
                SetVolume(reps=10, weight=weight, percent=70.0, muscle="back"),
            ]

        report = volume_report(self._build(muscles, days=self.SPAN_DAYS), weeks=4)
        self.assertEqual(report.trend, "falling")
        self.assertEqual(report.verdict, "容量有所下滑")

    def test_low_muscle_advice(self):
        def muscles(index):
            return [SetVolume(reps=1, weight=5.0, percent=20.0, muscle="abs")]

        report = volume_report(self._build(muscles), weeks=4)
        self.assertTrue(any("偏低" in advice for advice in report.advice))

    def test_high_muscle_advice(self):
        # 每周 3 组 × 12 次 × 400kg × 95% ≈ 13680 强度加权 kg·次，
        # 高于 MUSCLE_VOLUME_CEILING（12000），应被判为偏高。
        def muscles(index):
            return [
                SetVolume(reps=12, weight=400.0, percent=95.0, muscle="legs"),
                SetVolume(reps=12, weight=400.0, percent=95.0, muscle="legs"),
                SetVolume(reps=12, weight=400.0, percent=95.0, muscle="legs"),
            ]

        report = volume_report(self._build(muscles), weeks=4)
        self.assertTrue(any("偏高" in advice for advice in report.advice))

    def test_rising_trend_advice(self):
        def muscles(index):
            weight = 60.0 + index * 8.0
            return [SetVolume(reps=10, weight=weight, percent=70.0, muscle="chest")]

        report = volume_report(self._build(muscles, days=self.SPAN_DAYS), weeks=4)
        self.assertEqual(report.trend, "rising")

    def test_as_dict_shape(self):
        def muscles(index):
            return [SetVolume(reps=10, weight=60.0, percent=70.0, muscle="chest")]

        report = volume_report(self._build(muscles), weeks=4).as_dict()
        for key in (
            "sessions",
            "weekly",
            "muscles",
            "total_tonnage",
            "total_effective_volume",
            "concentration",
            "trend",
            "verdict",
            "advice",
        ):
            self.assertIn(key, payload := report)
        self.assertIsInstance(payload["advice"], list)

    def test_report_with_insufficient_weeks_has_unknown_trend(self):
        def muscles(index):
            return [SetVolume(reps=10, weight=60.0, percent=70.0, muscle="chest")]

        report = volume_report(self._build(muscles, days=(0,)), weeks=4)
        self.assertEqual(report.trend, "unknown")

    def test_min_trend_weeks_constant(self):
        self.assertEqual(MIN_TREND_WEEKS, 3)


if __name__ == "__main__":
    unittest.main()
