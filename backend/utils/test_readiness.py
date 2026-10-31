"""准备度引擎的单测（纯 Python，不依赖 Django）。

运行方式：
    python -m unittest utils.test_readiness -v
"""

from __future__ import annotations

import unittest
from datetime import date, timedelta

from .readiness import (
    ACWR_DANGER,
    MONOTONY_ALERT,
    DailyLoad,
    acute_chronic_ratio,
    banister_impulse,
    build_daily_series,
    ewma,
    form_trend,
    linear_trend,
    monotony_strain,
    readiness_report,
    session_load,
    standard_deviation,
)

TODAY = date(2026, 5, 20)


def steady(days: int, load: float = 40.0, end: date = TODAY) -> list[DailyLoad]:
    """从 `end` 往前每隔一天训练一次的固定负荷序列。"""
    return [
        DailyLoad(day=end - timedelta(days=offset), load=load, minutes=load, form_score=80)
        for offset in range(days - 1, -1, -1)
        if offset % 2 == 0
    ]


class MathHelpersTests(unittest.TestCase):
    def test_ewma_of_a_constant_series_is_the_constant(self):
        self.assertAlmostEqual(ewma([5.0] * 30, 7), 5.0, places=6)

    def test_ewma_reacts_to_a_recent_spike(self):
        series = [10.0] * 20 + [100.0]
        self.assertGreater(ewma(series, 7), ewma(series, 28))

    def test_ewma_handles_empty_input(self):
        self.assertEqual(ewma([], 7), 0.0)
        self.assertEqual(ewma([1.0], 0), 0.0)

    def test_linear_trend_of_a_ramp(self):
        self.assertAlmostEqual(linear_trend([1.0, 2.0, 3.0, 4.0]), 1.0, places=6)
        self.assertAlmostEqual(linear_trend([4.0, 3.0, 2.0, 1.0]), -1.0, places=6)

    def test_linear_trend_of_flat_or_short_input(self):
        self.assertAlmostEqual(linear_trend([7.0, 7.0, 7.0]), 0.0, places=6)
        self.assertEqual(linear_trend([3.0]), 0.0)
        self.assertEqual(linear_trend([]), 0.0)

    def test_sample_standard_deviation(self):
        self.assertAlmostEqual(standard_deviation([2.0, 4.0, 4.0, 4.0, 5.0, 5.0, 7.0, 9.0]), 2.138089, places=5)
        self.assertEqual(standard_deviation([1.0]), 0.0)


class SeriesTests(unittest.TestCase):
    def test_build_daily_series_is_dense_and_aligned(self):
        series = build_daily_series([DailyLoad(day=TODAY, load=10)], TODAY, days=10)
        self.assertEqual(len(series), 10)
        self.assertEqual(series[-1], 10.0)
        self.assertEqual(series[:-1], [0.0] * 9)

    def test_build_daily_series_keeps_only_the_window(self):
        old = DailyLoad(day=TODAY - timedelta(days=50), load=99)
        series = build_daily_series([old], TODAY, days=10)
        self.assertEqual(sum(series), 0.0)

    def test_build_daily_series_is_deterministic(self):
        loads = steady(30)
        self.assertEqual(build_daily_series(loads, TODAY), build_daily_series(loads, TODAY))


class BanisterTests(unittest.TestCase):
    def test_a_single_session_today_creates_pure_fatigue(self):
        fitness, fatigue, tsb = banister_impulse([0.0] * 29 + [100.0])
        self.assertAlmostEqual(fitness, 100.0, places=6)
        self.assertAlmostEqual(fatigue, 100.0, places=6)
        self.assertAlmostEqual(tsb, 0.0, places=6)

    def test_tsb_turns_positive_after_a_taper(self):
        """停训一周后疲劳衰减快于体能，TSB 应该转正 —— 这就是"减量备赛"的原理。"""
        series = [0.0] * 30
        series[20] = 100.0  # 10 天前的一次大负荷
        fitness, fatigue, tsb = banister_impulse(series)
        self.assertGreater(tsb, 0.0)
        self.assertGreater(fitness, fatigue)

    def test_fatigue_decays_faster_than_fitness(self):
        series = [0.0] * 30
        series[15] = 100.0
        fitness, fatigue, _ = banister_impulse(series)
        self.assertGreater(fitness, fatigue)

    def test_zero_series_is_a_no_op(self):
        self.assertEqual(banister_impulse([0.0] * 10), (0.0, 0.0, 0.0))


class AcwrTests(unittest.TestCase):
    def test_constant_load_sits_in_the_sweet_spot(self):
        _, _, ratio = acute_chronic_ratio([30.0] * 60)
        self.assertAlmostEqual(ratio, 1.0, places=2)

    def test_a_recent_spike_pushes_the_ratio_above_one(self):
        _, _, ratio = acute_chronic_ratio([30.0] * 60 + [200.0])
        self.assertGreater(ratio, ACWR_DANGER)

    def test_a_taper_drops_the_ratio_below_one(self):
        _, _, ratio = acute_chronic_ratio([30.0] * 60 + [0.0] * 14)
        self.assertLess(ratio, 0.8)

    def test_new_users_get_a_neutral_ratio(self):
        _, chronic, ratio = acute_chronic_ratio([0.0] * 30)
        self.assertEqual(chronic, 0.0)
        self.assertEqual(ratio, 1.0)


class MonotonyTests(unittest.TestCase):
    def test_identical_weeks_are_flagged_as_monotonous(self):
        monotony, strain = monotony_strain([40.0] * 28)
        self.assertGreater(monotony, MONOTONY_ALERT)
        self.assertGreater(strain, 0.0)

    def test_varied_weeks_lower_the_monotony(self):
        varied = [10.0] * 7 + [60.0] * 7 + [20.0] * 7 + [55.0] * 7
        flat = [36.25] * 28
        self.assertLess(monotony_strain(varied)[0], monotony_strain(flat)[0])

    def test_empty_series(self):
        self.assertEqual(monotony_strain([]), (0.0, 0.0))


class FormTrendTests(unittest.TestCase):
    def test_trend_reads_the_last_scores_only(self):
        scores = [60.0] * 20 + [70.0, 74.0, 78.0, 82.0]
        self.assertGreater(form_trend(scores), 0.0)

    def test_missing_scores_are_ignored(self):
        self.assertGreater(form_trend([None, 60.0, 70.0, 80.0]), 0.0)
        self.assertEqual(form_trend([]), 0.0)


class SessionLoadTests(unittest.TestCase):
    def test_load_scales_with_performance(self):
        # 项目里的表现分是 0-5 分制
        self.assertGreater(session_load(30, 4.5), session_load(30, 2.5))

    def test_intensity_stays_inside_the_expected_band(self):
        self.assertAlmostEqual(session_load(60, 5.0) / 60, 1.0, places=6)
        self.assertAlmostEqual(session_load(60, 1.0) / 60, 0.7, places=6)

    def test_a_missing_performance_score_defaults_to_even_intensity(self):
        self.assertAlmostEqual(session_load(40, 0), 40.0, places=6)

    def test_absurd_durations_are_capped(self):
        self.assertLessEqual(session_load(600, 5), 180.0)

    def test_negative_minutes_are_ignored(self):
        self.assertEqual(session_load(-10, 4), 0.0)


class ReadinessReportTests(unittest.TestCase):
    def test_empty_history_gives_a_middle_of_the_road_score(self):
        report = readiness_report([], TODAY)
        self.assertEqual(report.components.session_count, 0)
        self.assertEqual(report.components.rest_days, -1)
        self.assertTrue(20 <= report.score <= 99)
        self.assertIn(report.tone, {"excellent", "good", "moderate", "recover"})

    def test_consistent_training_reads_as_ready(self):
        report = readiness_report(steady(60), TODAY)
        self.assertGreaterEqual(report.score, 60)
        self.assertIn(report.intensity, {"moderate", "hard"})
        self.assertGreater(report.components.chronic_load, 0.0)

    def test_a_sharp_spike_is_downgraded(self):
        base = steady(60, load=30)
        spike = base + [
            DailyLoad(day=TODAY - timedelta(days=1), load=170, minutes=170, form_score=70),
            DailyLoad(day=TODAY, load=170, minutes=170, form_score=68),
        ]
        spiked = readiness_report(spike, TODAY)
        steady_report = readiness_report(base, TODAY)
        self.assertLess(spiked.score, steady_report.score)
        self.assertGreater(spiked.components.acwr, steady_report.components.acwr)
        self.assertIn(spiked.intensity, {"light", "rest", "moderate"})

    def test_training_today_costs_a_little(self):
        base = steady(40, end=TODAY - timedelta(days=1))
        today_again = base + [DailyLoad(day=TODAY, load=40, minutes=40, form_score=80)]
        self.assertLess(readiness_report(today_again, TODAY).score, readiness_report(base, TODAY).score)

    def test_two_days_of_rest_is_the_supercompensation_window(self):
        rested = steady(40, end=TODAY - timedelta(days=2))
        report = readiness_report(rested, TODAY)
        self.assertEqual(report.components.rest_days, 2)
        self.assertTrue(any("超量恢复" in r for r in report.reasons))

    def test_a_long_layoff_is_penalised(self):
        stale = steady(40, end=TODAY - timedelta(days=21))
        report = readiness_report(stale, TODAY)
        self.assertEqual(report.components.rest_days, 21)
        self.assertTrue(any("休息" in r for r in report.reasons))

    def test_improving_form_scores_add_points(self):
        # 按时间正序构造：最旧的一天在前，最新的一天（今天）在后。
        rising = [
            DailyLoad(day=TODAY - timedelta(days=9 - i), load=40, minutes=40, form_score=60 + i * 2)
            for i in range(10)
        ]
        falling = [
            DailyLoad(day=TODAY - timedelta(days=9 - i), load=40, minutes=40, form_score=90 - i * 2)
            for i in range(10)
        ]
        self.assertGreater(readiness_report(rising, TODAY).score, readiness_report(falling, TODAY).score)

    def test_cold_start_does_not_flag_a_new_user_as_overreaching(self):
        """只有一次训练时 ACWR 天然会飙高，冷启动保护必须把它压住。"""
        rookie = [DailyLoad(day=TODAY, load=45, minutes=45, form_score=75)]
        report = readiness_report(rookie, TODAY)
        self.assertNotIn("超过 1.5", " ".join(report.reasons))
        self.assertGreaterEqual(report.score, 55)

    def test_score_is_bounded_and_deterministic(self):
        loads = steady(90)
        first = readiness_report(loads, TODAY)
        second = readiness_report(loads, TODAY)
        self.assertEqual(first.score, second.score)
        self.assertEqual(first.as_dict(), second.as_dict())
        self.assertTrue(20 <= first.score <= 99)

    def test_as_dict_exposes_every_component(self):
        payload = readiness_report(steady(30), TODAY).as_dict()
        for key in (
            "score",
            "tone",
            "label",
            "advice",
            "intensity",
            "volume_multiplier",
            "acwr",
            "fitness",
            "fatigue",
            "tsb",
            "monotony",
            "strain",
            "form_trend",
            "rest_days",
            "weekly_load",
            "weekly_loads",
            "session_count",
            "reasons",
        ):
            self.assertIn(key, payload)

    def test_weekly_loads_cover_the_last_four_weeks(self):
        payload = readiness_report(steady(60), TODAY).as_dict()
        self.assertEqual(len(payload["weekly_loads"]), 4)
        self.assertTrue(all(value > 0 for value in payload["weekly_loads"]))
        # 最后一周的周负荷应与 `weekly_load`（近 7 天）一致
        self.assertAlmostEqual(payload["weekly_loads"][-1], payload["weekly_load"], places=6)

    def test_weekly_loads_is_empty_without_history(self):
        payload = readiness_report([], TODAY).as_dict()
        self.assertEqual(payload["weekly_loads"], [])
        self.assertEqual(payload["monotony"], 0.0)

    def test_volume_multiplier_sits_in_a_safe_range(self):
        for loads in (steady(60), steady(60, load=150), []):
            report = readiness_report(loads, TODAY)
            self.assertTrue(0.35 <= report.volume_multiplier <= 1.15)


if __name__ == "__main__":
    unittest.main()
