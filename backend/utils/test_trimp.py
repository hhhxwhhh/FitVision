"""训练负荷分布引擎（TRIMP）的单元测试。

全部用例都不依赖 Django，可直接 `python -m unittest utils.test_trimp` 运行。
"""

import unittest
from datetime import date, timedelta

from utils.trimp import (
    HIGH_INTENSITY_SESSION_THRESHOLD,
    MAX_HIGH_INTENSITY_SETS_PER_WEEK,
    MIN_HIGH_INTENSITY_GAP_DAYS,
    ZONE_BOUNDS,
    ZONE_SHARE_TARGET,
    SetLoad,
    balance_score,
    distribution_report,
    high_intensity_gaps,
    percent_from_load,
    rpe_to_percent,
    session_profile,
    weekly_summary,
    zone_for_percent,
    zone_index,
)


def make_set(reps=10, weight=60.0, percent=None, rpe=None, e1rm=100.0):
    return SetLoad(
        reps=reps, weight=weight, percent=percent, rpe=rpe, e1rm=e1rm
    )


class RpeConversionTests(unittest.TestCase):
    def test_rpe_ten_maps_to_one_hundred_percent(self):
        self.assertAlmostEqual(rpe_to_percent(10), 100.0)

    def test_rpe_is_clamped_to_the_valid_range(self):
        self.assertGreaterEqual(rpe_to_percent(12), 90)
        self.assertIsNone(rpe_to_percent(-3))

    def test_invalid_rpe_returns_none(self):
        self.assertIsNone(rpe_to_percent(0))
        self.assertIsNone(rpe_to_percent(None))

    def test_lower_rpe_gives_lower_intensity(self):
        self.assertLess(rpe_to_percent(7), rpe_to_percent(9))


class PercentFromLoadTests(unittest.TestCase):
    def test_weight_relative_to_e1rm_gives_a_percentage(self):
        # 60kg × 3 次 → Epley 等效 1RM = 66kg，相对 100kg 的 1RM 即 66%。
        percent = percent_from_load(60.0, 3, 100.0)
        self.assertIsNotNone(percent)
        self.assertAlmostEqual(percent, 66.0, delta=1.0)

    def test_more_reps_means_a_harder_set(self):
        # 同样的重量做更多次 → 更接近力竭 → 等效强度更高。
        heavy = percent_from_load(80.0, 3, 100.0)
        light = percent_from_load(80.0, 10, 100.0)
        self.assertGreater(light, heavy)

    def test_percentage_is_capped_at_one_hundred(self):
        self.assertLessEqual(percent_from_load(150.0, 5, 100.0), 100.0)

    def test_bodyweight_exercise_has_no_percentage(self):
        self.assertIsNone(percent_from_load(0.0, 20, 100.0))

    def test_missing_e1rm_returns_none(self):
        self.assertIsNone(percent_from_load(60.0, 5, 0))

    def test_zero_reps_returns_none(self):
        self.assertIsNone(percent_from_load(60.0, 0, 100.0))


class ZoneTests(unittest.TestCase):
    def test_zone_boundaries(self):
        self.assertEqual(zone_index(50), 0)
        self.assertEqual(zone_for_percent(60)[0], "zone_2")
        self.assertEqual(zone_for_percent(75)[0], "zone_3")
        self.assertEqual(zone_for_percent(85)[0], "zone_4")
        self.assertEqual(zone_for_percent(100)[0], "zone_4")

    def test_zone_label_is_human_readable(self):
        self.assertEqual(zone_for_percent(90), ("zone_4", "强度"))
        self.assertEqual(zone_for_percent(10), ("zone_1", "恢复"))

    def test_zone_bounds_are_ordered(self):
        bounds = [item[0] for item in ZONE_BOUNDS]
        self.assertEqual(bounds, sorted(bounds))


class SessionProfileTests(unittest.TestCase):
    def test_empty_session_reports_no_measurable_sets(self):
        profile = session_profile([])
        self.assertEqual(profile.sets, 0)
        self.assertFalse(profile.balanced)
        self.assertTrue(profile.notes)

    def test_unmeasurable_sets_are_skipped(self):
        # 没有重量、没有 RPE 的组不该被计入。
        profile = session_profile([SetLoad(reps=10, weight=0.0, e1rm=0.0)])
        self.assertEqual(profile.sets, 0)

    def test_sets_are_counted_per_zone(self):
        sets = [
            make_set(percent=50),
            make_set(percent=55),
            make_set(percent=70),
            make_set(percent=80),
            make_set(percent=90),
        ]
        profile = session_profile(sets)
        zone_map = profile.zone_map
        self.assertEqual(zone_map["zone_1"].sets, 2)
        self.assertEqual(zone_map["zone_2"].sets, 1)
        self.assertEqual(zone_map["zone_3"].sets, 1)
        self.assertEqual(zone_map["zone_4"].sets, 1)
        self.assertEqual(profile.sets, 5)

    def test_shares_sum_to_one(self):
        profile = session_profile([make_set(percent=50), make_set(percent=90)])
        total = sum(zone.share for zone in profile.zones)
        self.assertAlmostEqual(total, 1.0, places=6)

    def test_high_intensity_sets_are_counted(self):
        profile = session_profile([make_set(percent=90), make_set(percent=95)])
        self.assertEqual(profile.high_intensity_sets, 2)

    def test_balanced_session_has_no_warning_note(self):
        # 目标分布 15/40/30/15，构造 10/40/30/20 应该在容差内。
        sets = [make_set(percent=50)] * 10
        sets += [make_set(percent=70)] * 40
        sets += [make_set(percent=80)] * 30
        sets += [make_set(percent=90)] * 20
        profile = session_profile(sets)
        self.assertTrue(profile.balanced)
        self.assertEqual(profile.notes, ())

    def test_heavy_session_is_flagged(self):
        sets = [make_set(percent=90)] * 9 + [make_set(percent=70)]
        profile = session_profile(sets)
        self.assertFalse(profile.balanced)
        self.assertTrue(profile.notes)

    def test_rpe_trimp_is_reps_times_rpe(self):
        profile = session_profile([make_set(reps=10, rpe=8), make_set(reps=10, rpe=8)])
        self.assertAlmostEqual(profile.rpe_trimp, 160.0, delta=0.1)

    def test_intensity_trimp_is_reps_times_percent(self):
        profile = session_profile([make_set(reps=10, percent=80)])
        self.assertAlmostEqual(profile.intensity_trimp, 800.0, delta=0.1)

    def test_explicit_percent_wins_over_rpe(self):
        profile = session_profile([make_set(reps=10, percent=90, rpe=6)])
        self.assertEqual(profile.high_intensity_sets, 1)

    def test_rpe_only_sets_still_land_in_a_zone(self):
        profile = session_profile([make_set(reps=10, rpe=9)])
        self.assertEqual(profile.sets, 1)
        self.assertEqual(profile.zone_map["zone_4"].sets, 1)

    def test_session_carries_the_date(self):
        day = date(2026, 3, 1)
        profile = session_profile([make_set(percent=70)], day=day)
        self.assertEqual(profile.date, day)
        self.assertEqual(profile.as_dict()["date"], "2026-03-01")


class WeeklySummaryTests(unittest.TestCase):
    def _sessions(self):
        base = date(2026, 3, 2)
        sessions = []
        for index in range(3):
            sessions.append(
                session_profile(
                    [make_set(percent=70)] * 4 + [make_set(percent=90)] * 2,
                    day=base + timedelta(days=index * 7),
                )
            )
        return sessions

    def test_weekly_summary_groups_by_iso_week(self):
        summary = weekly_summary(self._sessions(), weeks=4)
        self.assertEqual(len(summary), 3)

    def test_weekly_summary_counts_sets(self):
        summary = weekly_summary(self._sessions(), weeks=4)
        self.assertEqual(summary[0]["sets"], 6)
        self.assertEqual(summary[0]["sessions"], 1)

    def test_weekly_summary_flags_the_high_intensity_cap(self):
        sessions = [
            session_profile(
                [make_set(percent=90)] * (MAX_HIGH_INTENSITY_SETS_PER_WEEK + 1),
                day=date(2026, 3, 2),
            )
        ]
        summary = weekly_summary(sessions, weeks=4)
        self.assertTrue(summary[0]["over_high_intensity_cap"])

    def test_weekly_summary_limits_the_window(self):
        sessions = self._sessions() * 4
        summary = weekly_summary(sessions, weeks=2)
        self.assertEqual(len(summary), 2)


class BalanceScoreTests(unittest.TestCase):
    def test_perfect_distribution_scores_one(self):
        sets = []
        for percent, count in zip((50, 70, 80, 90), (15, 40, 30, 15)):
            sets += [make_set(percent=percent)] * count
        profile = session_profile(sets)
        self.assertAlmostEqual(balance_score([profile]), 1.0, places=3)

    def test_all_high_intensity_scores_low(self):
        profile = session_profile([make_set(percent=92)] * 10)
        self.assertLess(balance_score([profile]), 0.4)

    def test_no_data_scores_zero(self):
        self.assertEqual(balance_score([]), 0.0)


class HighIntensityGapTests(unittest.TestCase):
    def test_gaps_are_measured_between_high_intensity_days(self):
        sessions = [
            session_profile(
                [make_set(percent=90)] * HIGH_INTENSITY_SESSION_THRESHOLD,
                day=date(2026, 3, 1),
            ),
            session_profile(
                [make_set(percent=90)] * HIGH_INTENSITY_SESSION_THRESHOLD,
                day=date(2026, 3, 4),
            ),
        ]
        self.assertEqual(high_intensity_gaps(sessions), (3,))

    def test_light_days_do_not_count_as_high_intensity(self):
        sessions = [
            session_profile([make_set(percent=60)] * 8, day=date(2026, 3, 1)),
            session_profile([make_set(percent=60)] * 8, day=date(2026, 3, 2)),
        ]
        self.assertEqual(high_intensity_gaps(sessions), ())


class DistributionReportTests(unittest.TestCase):
    def test_report_without_data_says_so(self):
        report = distribution_report([])
        self.assertEqual(report.verdict, "数据不足")
        self.assertTrue(report.advice)

    def test_balanced_training_is_praised(self):
        sets = []
        for percent, count in zip((50, 70, 80, 90), (15, 40, 30, 15)):
            sets += [make_set(percent=percent)] * count
        profile = session_profile(sets, day=date(2026, 3, 1))
        report = distribution_report([profile])
        self.assertEqual(report.verdict, "分布良好")
        self.assertGreaterEqual(report.balance_score, 0.9)

    def test_heavy_distribution_is_advised_down(self):
        sets = [make_set(percent=90)] * 12 + [make_set(percent=60)] * 2
        profile = session_profile(sets, day=date(2026, 3, 1))
        report = distribution_report([profile])
        self.assertNotEqual(report.verdict, "分布良好")
        self.assertTrue(any("高强度" in item for item in report.advice))

    def test_report_serialises(self):
        profile = session_profile([make_set(percent=70)], day=date(2026, 3, 1))
        payload = distribution_report([profile]).as_dict()
        self.assertIn("sessions", payload)
        self.assertIn("balance_score", payload)
        self.assertEqual(payload["sessions"][0]["sets"], 1)


if __name__ == "__main__":
    unittest.main()
