"""力量评估引擎的单元测试（纯 Python，`python -m unittest utils.test_strength`）。"""

from __future__ import annotations

import unittest
from datetime import date

from .strength import (
    DECLINE_THRESHOLD,
    MAX_REPS_FOR_ESTIMATE,
    PLATE_INCREMENT,
    SetResult,
    best_e1rm,
    best_set_estimate,
    build_sets,
    brzycki_1rm,
    compare_estimates,
    deload_advice,
    e1rm_trend,
    epley_1rm,
    estimate_1rm,
    estimate_1rm_from_rir,
    estimate_1rm_from_velocity,
    estimate_session_e1rm,
    lombardi_1rm,
    next_prescription,
    prescribe_load,
    rep_formula_estimates,
    rep_percentage,
    rir_from_rpe,
    round_to_increment,
    strength_summary,
    velocity_rep_capacity,
    wathan_1rm,
)


class OneRepMaxFormulaTests(unittest.TestCase):
    def test_one_rep_returns_the_weight_itself(self):
        self.assertAlmostEqual(epley_1rm(100, 1), 100.0)
        self.assertAlmostEqual(brzycki_1rm(100, 1), 100.0)
        self.assertAlmostEqual(lombardi_1rm(100, 1), 100.0)
        # Wathan 是回归公式，单次时约 101.3%（因此保守估计会取最小值）
        self.assertAlmostEqual(wathan_1rm(100, 1), 100.0, delta=1.5)

    def test_epley_formula(self):
        self.assertAlmostEqual(epley_1rm(100, 5), 100 * (1 + 5 / 30))
        self.assertAlmostEqual(epley_1rm(100, 10), 100 * (1 + 10 / 30))

    def test_brzycki_is_more_conservative_than_epley(self):
        self.assertLess(brzycki_1rm(100, 8), epley_1rm(100, 8))

    def test_wathan_matches_epley_around_five_reps(self):
        self.assertAlmostEqual(wathan_1rm(100, 5), epley_1rm(100, 5), delta=0.5)

    def test_all_formulas_increase_with_reps(self):
        for reps in (2, 5, 8, 12):
            values = rep_formula_estimates(100, reps)
            self.assertGreaterEqual(min(values.values()), 100.0)
            self.assertLess(max(values.values()), 145.0)

    def test_zero_reps_yields_nothing(self):
        self.assertEqual(epley_1rm(100, 0), 0.0)
        self.assertEqual(rep_formula_estimates(100, 0), {})

    def test_brzycki_refuses_more_than_36_reps(self):
        self.assertEqual(brzycki_1rm(100, 40), 0.0)


class EstimateOneRepMaxTests(unittest.TestCase):
    def test_returns_none_without_weight_or_reps(self):
        self.assertIsNone(estimate_1rm(0, 10))
        self.assertIsNone(estimate_1rm(100, 0))

    def test_refuses_to_estimate_beyond_the_rep_limit(self):
        self.assertIsNone(estimate_1rm(100, MAX_REPS_FOR_ESTIMATE + 1))

    def test_takes_the_most_conservative_formula(self):
        estimate = estimate_1rm(100, 8)
        assert estimate is not None
        self.assertAlmostEqual(estimate.e1rm, min(rep_formula_estimates(100, 8).values()), places=6)

    def test_confidence_decreases_with_reps(self):
        low = estimate_1rm(100, 2)
        high = estimate_1rm(100, 11)
        assert low is not None and high is not None
        self.assertGreater(low.confidence, high.confidence)
        self.assertGreaterEqual(high.confidence, 0.4)

    def test_details_carry_the_inputs(self):
        estimate = estimate_1rm(80, 6)
        assert estimate is not None
        self.assertEqual(estimate.details["weight"], 80)
        self.assertEqual(estimate.details["reps"], 6)
        self.assertIn("estimates", estimate.details)


class VelocityTests(unittest.TestCase):
    def test_velocity_at_one_rep_means_one_rep(self):
        self.assertAlmostEqual(velocity_rep_capacity(0.30), 1.0)

    def test_faster_means_more_reps(self):
        self.assertGreater(velocity_rep_capacity(0.60), velocity_rep_capacity(0.40))

    def test_capacity_is_capped(self):
        self.assertLessEqual(velocity_rep_capacity(2.0), 15.0)

    def test_junk_velocity_returns_zero(self):
        self.assertEqual(velocity_rep_capacity(0), 0.0)
        self.assertEqual(velocity_rep_capacity(-1), 0.0)

    def test_velocity_estimate_scales_the_weight(self):
        estimate = estimate_1rm_from_velocity(100, 0.5)
        assert estimate is not None
        self.assertGreater(estimate.e1rm, 100)
        self.assertEqual(estimate.method, "velocity")

    def test_velocity_estimate_needs_a_weight(self):
        self.assertIsNone(estimate_1rm_from_velocity(0, 0.5))
        self.assertIsNone(estimate_1rm_from_velocity(100, 0))


class RpeRirTests(unittest.TestCase):
    def test_rpe_ten_means_no_reps_in_reserve(self):
        self.assertAlmostEqual(rir_from_rpe(10), 0.0)

    def test_rpe_eight_means_two_in_reserve(self):
        self.assertAlmostEqual(rir_from_rpe(8), 2.0)

    def test_rir_is_clamped(self):
        self.assertAlmostEqual(rir_from_rpe(1), 5.0)
        self.assertAlmostEqual(rir_from_rpe(0), 0.0)

    def test_percentage_matches_the_standard_chart(self):
        self.assertAlmostEqual(rep_percentage(1, 0), 1.0)
        self.assertAlmostEqual(rep_percentage(5, 2), 0.833, places=3)
        self.assertAlmostEqual(rep_percentage(10, 2), 0.732, places=3)

    def test_more_reserve_means_a_heavier_percentage(self):
        self.assertGreater(rep_percentage(5, 0), rep_percentage(5, 2))

    def test_rir_estimate_inverts_the_percentage(self):
        estimate = estimate_1rm_from_rir(100, 5, 2)
        assert estimate is not None
        self.assertAlmostEqual(estimate.e1rm, 100 / rep_percentage(5, 2), places=6)
        self.assertEqual(estimate.method, "rir")

    def test_rir_estimate_requires_data(self):
        self.assertIsNone(estimate_1rm_from_rir(0, 5, 2))
        self.assertIsNone(estimate_1rm_from_rir(100, 0, 2))


class SetSelectionTests(unittest.TestCase):
    def test_prefers_velocity_when_available(self):
        sets = [SetResult(weight=100, reps=5, mean_velocity=0.4)]
        estimate = best_set_estimate(sets)
        assert estimate is not None
        self.assertEqual(estimate.method, "velocity")

    def test_falls_back_to_rir(self):
        sets = [SetResult(weight=100, reps=5, rir=2)]
        estimate = best_set_estimate(sets)
        assert estimate is not None
        self.assertEqual(estimate.method, "rir")

    def test_falls_back_to_the_rep_formula(self):
        sets = [SetResult(weight=100, reps=5)]
        estimate = best_set_estimate(sets)
        assert estimate is not None
        self.assertEqual(estimate.method, "rep_formula")

    def test_no_sets_means_no_estimate(self):
        self.assertIsNone(best_set_estimate([]))
        self.assertIsNone(best_set_estimate([SetResult(weight=0, reps=0)]))

    def test_session_estimate_uses_the_heaviest_set(self):
        sets = [
            SetResult(weight=60, reps=10),
            SetResult(weight=100, reps=3),
            SetResult(weight=80, reps=6),
        ]
        session = estimate_session_e1rm(sets)
        heaviest = best_set_estimate([sets[1]])
        assert session is not None and heaviest is not None
        self.assertAlmostEqual(session.e1rm, heaviest.e1rm, places=6)

    def test_session_estimate_ignores_bodyweight_moves(self):
        sets = [SetResult(weight=0, reps=20, mean_velocity=0.5), SetResult(weight=60, reps=8)]
        session = estimate_session_e1rm(sets)
        assert session is not None
        self.assertGreater(session.e1rm, 60)

    def test_best_e1rm_takes_the_maximum(self):
        low = estimate_1rm(100, 5)
        high = estimate_1rm(120, 3)
        self.assertAlmostEqual(best_e1rm([low, high, None]), best_e1rm([high]))
        self.assertEqual(best_e1rm([]), 0.0)


class ComparisonTests(unittest.TestCase):
    def test_a_single_source_is_always_consistent(self):
        result = compare_estimates([estimate_1rm(100, 5)])
        self.assertTrue(result["consistent"])
        self.assertEqual(result["count"], 1)

    def test_close_estimates_are_consistent(self):
        a = estimate_1rm(100, 5)
        b = estimate_1rm_from_velocity(100, 0.48)
        result = compare_estimates([a, b])
        self.assertTrue(result["consistent"])
        self.assertGreater(result["mean"], 0)

    def test_wildly_different_estimates_are_flagged(self):
        a = estimate_1rm(100, 5)
        b = estimate_1rm_from_velocity(300, 0.9)
        result = compare_estimates([a, b])
        self.assertFalse(result["consistent"])

    def test_no_estimates(self):
        result = compare_estimates([])
        self.assertEqual(result["count"], 0)
        self.assertTrue(result["consistent"])


class PrescriptionTests(unittest.TestCase):
    def test_rounds_down_to_the_plate_increment(self):
        self.assertAlmostEqual(round_to_increment(101.3, 2.5), 100.0)
        self.assertAlmostEqual(round_to_increment(102.5, 2.5), 102.5)

    def test_rounding_handles_junk(self):
        self.assertEqual(round_to_increment(0), 0.0)
        self.assertAlmostEqual(round_to_increment(50, 0), 50.0)

    def test_prescribed_load_follows_the_percentage_table(self):
        load = prescribe_load(100, 5, target_rir=2)
        self.assertAlmostEqual(load, round_to_increment(100 * rep_percentage(5, 2), PLATE_INCREMENT))

    def test_prescribed_load_is_zero_without_a_baseline(self):
        self.assertEqual(prescribe_load(0, 5), 0.0)

    def test_completing_the_rep_range_adds_weight(self):
        prescription = next_prescription(120, 100, 6, 6)
        self.assertTrue(prescription.changed)
        self.assertGreater(prescription.weight, 100)

    def test_missing_the_rep_range_keeps_the_weight(self):
        prescription = next_prescription(120, 100, 4, 6)
        self.assertFalse(prescription.changed)
        self.assertAlmostEqual(prescription.weight, 100.0)

    def test_the_first_prescription_starts_from_the_baseline(self):
        prescription = next_prescription(120, 0, 0, 6)
        self.assertFalse(prescription.changed)
        self.assertGreater(prescription.weight, 0)

    def test_without_a_baseline_there_is_nothing_to_say(self):
        prescription = next_prescription(0, 0, 0, 6)
        self.assertEqual(prescription.weight, 0.0)
        self.assertFalse(prescription.changed)

    def test_prescription_serialises(self):
        payload = next_prescription(120, 100, 6, 6).as_dict()
        self.assertIn("weight", payload)
        self.assertIn("reason", payload)


class TrendTests(unittest.TestCase):
    def test_an_increasing_series_has_a_positive_slope(self):
        self.assertGreater(e1rm_trend([100, 105, 110]), 0)

    def test_a_flat_series_has_no_slope(self):
        self.assertAlmostEqual(e1rm_trend([100, 100, 100]), 0.0)

    def test_too_few_samples(self):
        self.assertEqual(e1rm_trend([]), 0.0)
        self.assertEqual(e1rm_trend([100]), 0.0)

    def test_zero_values_are_ignored(self):
        self.assertGreater(e1rm_trend([0, 100, 110]), 0)


class BuildSetsTests(unittest.TestCase):
    def test_pairs_weights_and_reps(self):
        sets = build_sets([60, 60], [10, 8])
        self.assertEqual(len(sets), 2)
        self.assertEqual(sets[0].weight, 60)
        self.assertEqual(sets[1].reps, 8)

    def test_handles_missing_lists(self):
        self.assertEqual(build_sets(None, None), [])
        self.assertEqual(build_sets([60], None), [])

    def test_truncates_to_the_shorter_list(self):
        self.assertEqual(len(build_sets([60, 60, 60], [10])), 1)

    def test_skips_junk_values(self):
        sets = build_sets(["60", "x"], [10, 8])
        self.assertEqual(sets[0].weight, 60)
        self.assertEqual(sets[1].weight, 0.0)
        self.assertEqual(sets[1].reps, 8)

    def test_negative_reps_are_clamped(self):
        sets = build_sets([60], [-5])
        self.assertEqual(sets[0].reps, 0)

    def test_rir_lands_on_the_heaviest_set(self):
        sets = build_sets([60, 100], [10, 5], rir=2)
        self.assertIsNone(sets[0].rir)
        self.assertEqual(sets[1].rir, 2)

    def test_rir_of_zero_is_kept(self):
        sets = build_sets([60], [10], rir=0)
        self.assertEqual(sets[0].rir, 0)

    def test_without_rir_no_set_carries_it(self):
        sets = build_sets([60], [10])
        self.assertIsNone(sets[0].rir)


class DeloadTests(unittest.TestCase):
    def test_progress_means_no_deload(self):
        advice = deload_advice([100, 105, 110])
        self.assertFalse(advice["deload"])
        self.assertEqual(advice["reasons"], [])

    def test_a_decline_triggers_a_deload(self):
        advice = deload_advice([120, 115, 110])
        self.assertTrue(advice["deload"])
        self.assertAlmostEqual(advice["factor"], 0.9)
        self.assertTrue(any("下降" in reason for reason in advice["reasons"]))

    def test_a_stall_triggers_a_deload(self):
        advice = deload_advice([100, 100, 100, 100])
        self.assertTrue(advice["deload"])
        self.assertTrue(any("没有提升" in reason for reason in advice["reasons"]))

    def test_high_fatigue_triggers_a_deload(self):
        advice = deload_advice([100, 110], fatigue=0.9)
        self.assertTrue(advice["deload"])
        self.assertTrue(any("疲劳" in reason for reason in advice["reasons"]))

    def test_a_small_decline_is_tolerated(self):
        decline = 100 * (1 - DECLINE_THRESHOLD / 2)
        advice = deload_advice([100, decline])
        self.assertFalse(advice["deload"])

    def test_the_advice_carries_a_prescription(self):
        advice = deload_advice([100, 100, 100])
        self.assertIn("advice", advice)


class SummaryTests(unittest.TestCase):
    def test_summarises_a_series(self):
        payload = strength_summary([100, 105, 110], [date(2026, 10, 1), date(2026, 10, 2), date(2026, 10, 3)])
        self.assertAlmostEqual(payload["latest"], 110.0)
        self.assertAlmostEqual(payload["best"], 110.0)
        self.assertEqual(payload["sessions"], 3)
        self.assertGreater(payload["trend"], 0)

    def test_handles_an_empty_series(self):
        payload = strength_summary([])
        self.assertEqual(payload["latest"], 0.0)
        self.assertFalse(payload["deload"]["deload"])

    def test_reports_the_first_session_date(self):
        payload = strength_summary([100, 105], [date(2026, 10, 1), date(2026, 10, 2)])
        self.assertEqual(payload["first_session"], "2026-10-01")


if __name__ == "__main__":
    unittest.main()
