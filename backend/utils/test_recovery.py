"""分肌群恢复模型的单元测试（纯 Python，`python -m unittest utils.test_recovery`）。"""

from __future__ import annotations

import unittest
from datetime import datetime, timedelta

from .recovery import (
    DEFAULT_CAPACITY,
    FATIGUED_THRESHOLD,
    MULTIPLIER_MIN,
    MUSCLE_ORDER,
    READY_THRESHOLD,
    MuscleWork,
    capacity_for,
    decay,
    halflife_for,
    hours_to_ready,
    label_for,
    multiplier_for_recovery,
    muscle_recovery,
    muscle_state,
    rebalance_multipliers,
    recovery_percent,
    residual_fatigue,
    status_for,
    stimulus,
    volume_status_for,
    weekly_sets,
)

NOW = datetime(2026, 10, 31, 20, 0, 0)


def work(muscle: str, hours_ago: float = 0.0, sets: int = 3, reps: int = 10,
         seconds: float = 0.0, form_score: float | None = None) -> MuscleWork:
    return MuscleWork(
        muscle=muscle,
        at=NOW - timedelta(hours=hours_ago),
        sets=sets,
        reps=reps,
        seconds=seconds,
        form_score=form_score,
    )


class StimulusTests(unittest.TestCase):
    def test_resistance_volume_is_normalised_to_ten_reps(self):
        self.assertAlmostEqual(stimulus(work("chest", sets=3, reps=10)), 3.0)

    def test_timed_holds_count_by_minute(self):
        self.assertAlmostEqual(stimulus(work("abs", sets=0, reps=0, seconds=180)), 3.0)

    def test_reps_and_seconds_add_up(self):
        self.assertAlmostEqual(stimulus(work("legs", sets=2, reps=12, seconds=120)), 4.4)

    def test_form_score_modulates_gently(self):
        poor = stimulus(work("back", form_score=50))
        good = stimulus(work("back", form_score=100))
        self.assertAlmostEqual(poor, 3.0)
        self.assertAlmostEqual(good, 3.3)
        self.assertLess(good - poor, poor * 0.2)

    def test_an_empty_record_contributes_nothing(self):
        self.assertEqual(stimulus(work("chest", sets=0, reps=0)), 0.0)

    def test_negative_inputs_are_clamped(self):
        self.assertEqual(stimulus(MuscleWork(muscle="abs", at=NOW, sets=-3, reps=-10, seconds=-60)), 0.0)

    def test_missing_form_score_is_neutral(self):
        self.assertAlmostEqual(stimulus(work("legs")), 3.0)


class DecayTests(unittest.TestCase):
    def test_half_of_the_fatigue_is_gone_after_one_halflife(self):
        self.assertAlmostEqual(decay(48.0, 48.0), 0.5, places=6)

    def test_nothing_has_decayed_at_zero_hours(self):
        self.assertAlmostEqual(decay(0.0, 48.0), 1.0)

    def test_clock_skew_does_not_amplify_fatigue(self):
        self.assertAlmostEqual(decay(-10.0, 48.0), 1.0)

    def test_far_future_work_is_almost_gone(self):
        self.assertLess(decay(24 * 20, 48.0), 0.01)


class MuscleMetadataTests(unittest.TestCase):
    def test_big_muscle_groups_recover_slower(self):
        self.assertGreater(halflife_for("legs"), halflife_for("abs"))
        self.assertGreater(halflife_for("back"), halflife_for("arms"))

    def test_unknown_muscles_fall_back_to_defaults(self):
        self.assertEqual(halflife_for("neck"), 48.0)
        self.assertEqual(capacity_for("neck"), DEFAULT_CAPACITY)

    def test_labels_are_chinese(self):
        self.assertEqual(label_for("chest"), "胸部")
        self.assertEqual(label_for("LEGS"), "腿部")

    def test_normalisation_tolerates_blank_values(self):
        self.assertEqual(label_for(""), "全身")
        self.assertEqual(label_for(None), "全身")


class ResidualFatigueTests(unittest.TestCase):
    def test_recent_work_leaves_more_residual_than_old_work(self):
        recent = residual_fatigue([work("chest", hours_ago=2)], "chest", NOW)
        old = residual_fatigue([work("chest", hours_ago=48)], "chest", NOW)
        self.assertGreater(recent, old)

    def test_synergy_muscles_absorb_a_share(self):
        residual = residual_fatigue([work("chest")], "shoulders", NOW)
        self.assertGreater(residual, 0.0)
        self.assertLess(residual, residual_fatigue([work("chest")], "chest", NOW))

    def test_abs_is_not_a_synergist_of_arms(self):
        self.assertEqual(residual_fatigue([work("arms")], "abs", NOW), 0.0)

    def test_leg_day_spills_into_glutes(self):
        self.assertGreater(residual_fatigue([work("legs")], "glutes", NOW), 0.0)

    def test_unrelated_muscle_is_untouched(self):
        self.assertEqual(residual_fatigue([work("chest")], "abs", NOW), 0.0)

    def test_future_records_do_not_create_negative_decay(self):
        future = MuscleWork(muscle="legs", at=NOW + timedelta(hours=5), sets=3, reps=10)
        self.assertAlmostEqual(residual_fatigue([future], "legs", NOW), 3.0)


class WeeklyVolumeTests(unittest.TestCase):
    def test_only_primary_muscle_sets_are_counted(self):
        items = [work("chest", hours_ago=24, sets=4)]
        self.assertEqual(weekly_sets(items, "chest", NOW), 4.0)
        self.assertEqual(weekly_sets(items, "shoulders", NOW), 0.0)

    def test_work_older_than_the_window_is_excluded(self):
        items = [work("back", hours_ago=24 * 9, sets=5)]
        self.assertEqual(weekly_sets(items, "back", NOW), 0.0)

    def test_volume_status_bands(self):
        self.assertEqual(volume_status_for(0), "idle")
        self.assertEqual(volume_status_for(6), "under")
        self.assertEqual(volume_status_for(14), "optimal")
        self.assertEqual(volume_status_for(26), "over")


class RecoveryMathTests(unittest.TestCase):
    def test_no_residual_means_fully_recovered(self):
        self.assertEqual(recovery_percent(0.0, 6.0), 100.0)

    def test_capacity_equals_zero_fatigue(self):
        self.assertEqual(recovery_percent(6.0, 6.0), 0.0)

    def test_recovery_is_clamped_to_zero(self):
        self.assertEqual(recovery_percent(20.0, 6.0), 0.0)

    def test_status_boundaries(self):
        self.assertEqual(status_for(READY_THRESHOLD), "ready")
        self.assertEqual(status_for(READY_THRESHOLD - 0.1), "caution")
        self.assertEqual(status_for(FATIGUED_THRESHOLD), "caution")
        self.assertEqual(status_for(FATIGUED_THRESHOLD - 0.1), "fatigued")

    def test_hours_to_ready_is_zero_when_already_ready(self):
        self.assertEqual(hours_to_ready(0.5, 6.0, 48.0), 0.0)

    def test_hours_to_ready_shrinks_as_time_passes(self):
        capacity, halflife = capacity_for("legs"), halflife_for("legs")
        fresh = hours_to_ready(9.0, capacity, halflife)
        later = hours_to_ready(2.25, capacity, halflife)
        self.assertGreater(fresh, later)

    def test_hours_to_ready_matches_one_halflife_step(self):
        # 残余为阈值的 4 倍时，需要 2 个半衰期才能降到阈值。
        self.assertAlmostEqual(hours_to_ready(4.0, 1.0 / 0.15, 48.0), 96.0, places=6)

    def test_multiplier_spans_the_documented_range(self):
        self.assertAlmostEqual(multiplier_for_recovery(0.0), MULTIPLIER_MIN)
        self.assertGreater(multiplier_for_recovery(100.0), 1.1)
        self.assertLess(multiplier_for_recovery(100.0), 1.2)

    def test_multiplier_is_monotonic(self):
        self.assertGreater(multiplier_for_recovery(80), multiplier_for_recovery(40))


class SnapshotTests(unittest.TestCase):
    def test_empty_history_marks_everything_ready(self):
        snapshot = muscle_recovery([], NOW)
        self.assertTrue(all(state.status == "ready" for state in snapshot.muscles.values()))
        self.assertEqual(snapshot.avoid, [])

    def test_a_fresh_leg_day_fatigues_legs(self):
        snapshot = muscle_recovery([work("legs", sets=4, reps=12)], NOW)
        self.assertIn("legs", snapshot.muscles)
        self.assertLess(snapshot.muscles["legs"].recovery, 100.0)

    def test_fresh_heavy_leg_day_keeps_legs_out_of_focus(self):
        items = [work("legs", hours_ago=1, sets=5, reps=12) for _ in range(3)]
        snapshot = muscle_recovery(items, NOW)
        self.assertNotIn("legs", snapshot.focus)
        self.assertIn("legs", snapshot.avoid)

    def test_recovered_muscles_win_the_focus(self):
        items = [
            work("legs", hours_ago=2, sets=5, reps=12),
            work("back", hours_ago=3, sets=5, reps=12),
            work("glutes", hours_ago=2, sets=4, reps=12),
            work("shoulders", hours_ago=2, sets=4, reps=12),
        ]
        snapshot = muscle_recovery(items, NOW)
        self.assertIn("chest", snapshot.focus)

    def test_focus_only_contains_ready_muscles(self):
        items = [
            work(key, hours_ago=6, sets=6, reps=12)
            for key in ("legs", "back", "chest", "shoulders", "glutes")
        ]
        snapshot = muscle_recovery(items, NOW)
        for key in snapshot.focus:
            self.assertEqual(snapshot.muscles[key].status, "ready")

    def test_focus_breaks_ties_by_weekly_volume(self):
        # 两块肌群同样完全恢复时，本周练得少的那个优先，起到均衡覆盖的作用。
        items = [
            work("chest", hours_ago=24 * 8, sets=6),
            work("back", hours_ago=24 * 8, sets=6),
            work("shoulders", hours_ago=24 * 8, sets=6),
        ]
        snapshot = muscle_recovery(items, NOW)
        self.assertEqual(len(snapshot.focus), 2)
        self.assertTrue(all(snapshot.muscles[key].weekly_sets == 0 for key in snapshot.focus))

    def test_focus_never_exceeds_two_muscles(self):
        self.assertLessEqual(len(muscle_recovery([], NOW).focus), 2)

    def test_over_volumed_muscles_are_not_recommended(self):
        items = [work("chest", hours_ago=24 * 6, sets=8) for _ in range(3)]
        snapshot = muscle_recovery(items, NOW)
        chest = snapshot.muscles["chest"]
        self.assertEqual(chest.volume_status, "over")
        self.assertNotIn("chest", snapshot.focus)

    def test_focus_falls_back_to_ready_muscles_when_all_are_over(self):
        items = [work(key, hours_ago=24 * 8, sets=10) for key in MUSCLE_ORDER for _ in range(3)]
        snapshot = muscle_recovery(items, NOW)
        self.assertTrue(snapshot.focus)

    def test_ordered_covers_every_declared_muscle(self):
        snapshot = muscle_recovery([], NOW)
        self.assertEqual(len(snapshot.ordered()), len(MUSCLE_ORDER))

    def test_as_dict_shape(self):
        payload = muscle_recovery([work("back")], NOW).as_dict()
        self.assertIn("muscles", payload)
        self.assertIn("focus", payload)
        self.assertIn("avoid", payload)
        first = payload["muscles"][0]
        for key in ("muscle", "label", "recovery", "status", "weekly_sets", "multiplier"):
            self.assertIn(key, first)

    def test_multiplier_lookup_is_case_insensitive(self):
        snapshot = muscle_recovery([work("legs", sets=5, reps=12)], NOW)
        self.assertLess(snapshot.multiplier_for("LEGS"), 1.0)

    def test_multiplier_lookup_defaults_for_unknown_muscles(self):
        snapshot = muscle_recovery([], NOW)
        self.assertEqual(snapshot.multiplier_for("neck"), 1.0)

    def test_rebalance_multipliers_covers_every_muscle(self):
        snapshot = muscle_recovery([work("chest")], NOW)
        self.assertEqual(set(rebalance_multipliers(snapshot)), set(snapshot.muscles))

    def test_specific_muscle_subset(self):
        snapshot = muscle_recovery([work("chest")], NOW, muscles=["chest", "arms"])
        self.assertEqual(set(snapshot.muscles), {"chest", "arms"})

    def test_synergy_only_muscle_can_still_be_cautioned(self):
        snapshot = muscle_recovery([work("chest", sets=6, reps=12)], NOW)
        self.assertLess(snapshot.muscles["arms"].recovery, 100.0)


class MuscleStateTests(unittest.TestCase):
    def test_state_reports_hours_to_ready(self):
        state = muscle_state([work("legs", sets=5, reps=12)], "legs", NOW)
        self.assertGreater(state.hours_to_ready, 0.0)
        self.assertEqual(state.label, "腿部")

    def test_state_is_consistent_between_recovery_and_status(self):
        state = muscle_state([work("abs", sets=2, reps=20)], "abs", NOW)
        self.assertEqual(state.status, status_for(state.recovery))


if __name__ == "__main__":
    unittest.main()
