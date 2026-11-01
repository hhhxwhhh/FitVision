"""`utils.periodization` 引擎的单元测试（不依赖 Django）。"""

import unittest

from utils.periodization import (
    AUTOREGULATION_MIN_FACTOR,
    DAY_LABELS,
    MUSCLE_GROUPS,
    MUSCLE_WEEKLY_TARGET,
    PHASES,
    PHASE_TEMPLATES,
    autoregulation_factor,
    build_mesocycle,
    phase_sequence,
    weekly_set_target,
)


def _state(muscle, recovery=95.0, weekly_sets=0.0, status="ready", volume_status="under"):
    return {
        "muscle": muscle,
        "label": muscle,
        "recovery": recovery,
        "residual": 0.0,
        "status": status,
        "hours_to_ready": 0.0,
        "weekly_sets": weekly_sets,
        "volume_status": volume_status,
        "multiplier": 1.0,
    }


def _strength(muscle, best, points=None, name=None):
    return {
        "exercise_id": 1,
        "name": name or f"{muscle}-press",
        "target_muscle": muscle,
        "best": best,
        "e1rm": best,
        "trend": 0.5,
        "points": points if points is not None else [
            {"date": "2026-10-28", "e1rm": best - 2, "weight": best * 0.6, "reps": 8, "method": "rir"},
            {"date": "2026-10-31", "e1rm": best, "weight": best * 0.7, "reps": 8, "method": "rir"},
        ],
        "summary": {},
    }


class PhaseSequenceTests(unittest.TestCase):
    def test_known_lengths_match_templates(self):
        for length, template in PHASE_TEMPLATES.items():
            self.assertEqual(phase_sequence(length), template)

    def test_invalid_length_falls_back(self):
        self.assertEqual(len(phase_sequence(0)), 1)
        self.assertEqual(len(phase_sequence(99)), 8)

    def test_all_phases_known(self):
        for length in range(1, 9):
            for phase in phase_sequence(length):
                self.assertIn(phase, PHASES)

    def test_long_cycles_end_with_deload_or_realization(self):
        self.assertEqual(phase_sequence(5)[-1], "deload")
        self.assertEqual(phase_sequence(4)[-1], "realization")


class AutoregulationTests(unittest.TestCase):
    def test_high_readiness_no_discount(self):
        self.assertEqual(autoregulation_factor(100), 1.0)
        self.assertEqual(autoregulation_factor(85), 1.0)

    def test_low_readiness_discounts(self):
        factor = autoregulation_factor(40)
        self.assertLess(factor, 1.0)
        self.assertGreaterEqual(factor, AUTOREGULATION_MIN_FACTOR)

    def test_zero_readiness_hits_floor(self):
        self.assertAlmostEqual(autoregulation_factor(0), AUTOREGULATION_MIN_FACTOR, places=3)

    def test_monotonic(self):
        values = [autoregulation_factor(score) for score in range(0, 101, 5)]
        self.assertEqual(values, sorted(values))


class WeeklyTargetTests(unittest.TestCase):
    def test_target_minus_done(self):
        self.assertAlmostEqual(weekly_set_target("chest", 0), MUSCLE_WEEKLY_TARGET["chest"])
        self.assertAlmostEqual(
            weekly_set_target("chest", 5), MUSCLE_WEEKLY_TARGET["chest"] - 5
        )

    def test_never_negative(self):
        self.assertEqual(weekly_set_target("chest", 999), 0.0)

    def test_unknown_muscle_default(self):
        self.assertGreater(weekly_set_target("unknown_muscle", 0), 0)


class MesocycleStructureTests(unittest.TestCase):
    def test_builds_requested_number_of_weeks(self):
        cycle = build_mesocycle(weeks=4, days_per_week=4)
        self.assertEqual(len(cycle.weeks), 4)
        self.assertEqual(cycle.days_per_week, 4)

    def test_week_payload_shape(self):
        cycle = build_mesocycle(
            muscle_states=[_state("chest")],
            strength_entries=[_strength("chest", 100)],
            weeks=4,
            days_per_week=2,
        )
        payload = cycle.as_dict()
        self.assertEqual(payload["total_weeks"], 4)
        self.assertGreater(payload["total_sets"], 0)
        week = payload["weeks"][0]
        for key in ("index", "phase", "label", "volume", "intensity", "reps_low", "reps_high", "sessions"):
            self.assertIn(key, week)
        session = week["sessions"][0]
        for key in ("index", "label", "focus", "slots", "total_sets"):
            self.assertIn(key, session)
        slot = session["slots"][0]
        for key in ("muscle", "label", "sets", "reps", "weight", "e1rm", "based_on_e1rm", "note"):
            self.assertIn(key, slot)

    def test_empty_input_produces_empty_weeks(self):
        cycle = build_mesocycle(weeks=3, days_per_week=3)
        self.assertEqual(len(cycle.weeks), 3)
        self.assertEqual(cycle.as_dict()["total_sets"], 0)

    def test_deload_week_has_lower_volume(self):
        cycle = build_mesocycle(
            muscle_states=[_state("chest")],
            strength_entries=[_strength("chest", 100)],
            weeks=5,
            days_per_week=2,
        )
        volumes = [week.volume for week in cycle.weeks]
        self.assertLess(volumes[-1], volumes[0])

    def test_days_per_week_clamped(self):
        cycle = build_mesocycle(muscle_states=[_state("chest")], weeks=2, days_per_week=99)
        self.assertLessEqual(cycle.days_per_week, 5)
        self.assertGreaterEqual(cycle.days_per_week, 1)

    def test_day_labels_valid(self):
        cycle = build_mesocycle(
            muscle_states=[_state("chest"), _state("back")],
            strength_entries=[_strength("chest", 100), _strength("back", 120)],
            weeks=3,
            days_per_week=3,
        )
        for week in cycle.weeks:
            for day in week.sessions:
                self.assertIn(day.label, DAY_LABELS)


class FocusSelectionTests(unittest.TestCase):
    def test_picks_ready_muscles(self):
        cycle = build_mesocycle(
            muscle_states=[_state("chest", recovery=98), _state("back", recovery=20, status="fatigued")],
            strength_entries=[],
            weeks=2,
            days_per_week=2,
        )
        self.assertIn("chest", cycle.focus)
        self.assertNotIn("back", cycle.focus)

    def test_fatigued_muscles_listed_as_avoid(self):
        cycle = build_mesocycle(
            muscle_states=[_state("chest"), _state("legs", recovery=30, status="fatigued")],
            weeks=2,
            days_per_week=2,
        )
        self.assertIn("legs", cycle.avoid)
        self.assertTrue(any("酸痛" in note for note in cycle.notes))

    def test_volume_gap_raises_priority(self):
        low = build_mesocycle(
            muscle_states=[_state("chest", weekly_sets=0), _state("back", weekly_sets=15)],
            weeks=2,
            days_per_week=2,
        )
        self.assertEqual(low.focus[0], "chest")

    def test_muscles_with_data_get_boost(self):
        cycle = build_mesocycle(
            muscle_states=[_state("chest"), _state("back")],
            strength_entries=[_strength("back", 150)],
            weeks=2,
            days_per_week=2,
        )
        self.assertEqual(cycle.focus[0], "back")

    def test_focus_limited_to_six(self):
        states = [_state(m) for m in ("chest", "back", "shoulders", "arms", "abs", "legs", "glutes")]
        cycle = build_mesocycle(muscle_states=states, weeks=2, days_per_week=3)
        self.assertLessEqual(len(cycle.focus), 6)


class SlotPrescriptionTests(unittest.TestCase):
    def test_weight_derived_from_e1rm(self):
        cycle = build_mesocycle(
            muscle_states=[_state("chest")],
            strength_entries=[_strength("chest", 100)],
            weeks=4,
            days_per_week=1,
        )
        slot = cycle.weeks[0].sessions[0].slots[0]
        self.assertTrue(slot.based_on_e1rm)
        self.assertGreater(slot.weight, 0)
        self.assertLessEqual(slot.weight, 100)

    def test_weight_respects_phase_intensity_cap(self):
        cycle = build_mesocycle(
            muscle_states=[_state("chest")],
            strength_entries=[_strength("chest", 100)],
            weeks=5,
            days_per_week=1,
        )
        deload = cycle.weeks[-1].sessions[0].slots[0]
        self.assertLessEqual(deload.weight / 100.0, PHASES["deload"]["intensity"] + 1e-6)

    def test_weight_rounded_to_plate_increment(self):
        cycle = build_mesocycle(
            muscle_states=[_state("chest")],
            strength_entries=[_strength("chest", 63.7)],
            weeks=4,
            days_per_week=1,
        )
        slot = cycle.weeks[0].sessions[0].slots[0]
        self.assertAlmostEqual((slot.weight / 2.5) % 1.0, 0.0, places=6)

    def test_no_strength_data_means_no_load(self):
        cycle = build_mesocycle(
            muscle_states=[_state("chest")],
            strength_entries=[],
            weeks=3,
            days_per_week=1,
        )
        slot = cycle.weeks[0].sessions[0].slots[0]
        self.assertFalse(slot.based_on_e1rm)
        self.assertEqual(slot.weight, 0.0)

    def test_reps_follow_phase_range(self):
        cycle = build_mesocycle(
            muscle_states=[_state("chest")],
            strength_entries=[_strength("chest", 100)],
            weeks=5,
            days_per_week=1,
        )
        for week in cycle.weeks:
            for day in week.sessions:
                for slot in day.slots:
                    self.assertGreaterEqual(slot.reps, week.reps_low)
                    self.assertLessEqual(slot.reps, week.reps_high)

    def test_note_mentions_last_session(self):
        cycle = build_mesocycle(
            muscle_states=[_state("chest")],
            strength_entries=[_strength("chest", 100)],
            weeks=3,
            days_per_week=1,
        )
        slot = cycle.weeks[0].sessions[0].slots[0]
        self.assertIn("上次", slot.note)


class GroupingTests(unittest.TestCase):
    def test_each_day_holds_a_single_movement_pattern(self):
        cycle = build_mesocycle(
            muscle_states=[_state("chest"), _state("shoulders"), _state("arms"), _state("back"), _state("legs")],
            strength_entries=[],
            weeks=2,
            days_per_week=3,
        )
        for week in cycle.weeks:
            for day in week.sessions:
                groups = {_group(muscle) for muscle in day.focus}
                self.assertEqual(len(groups), 1, f"一天里混了多个动作模式: {day.focus}")

    def test_different_groups_land_on_different_days(self):
        cycle = build_mesocycle(
            muscle_states=[_state("chest"), _state("back"), _state("legs")],
            strength_entries=[],
            weeks=2,
            days_per_week=3,
        )
        for week in cycle.weeks:
            day_groups = [{_group(muscle) for muscle in day.focus} for day in week.sessions]
            flattened = [g for group in day_groups for g in group]
            self.assertEqual(len(flattened), len(set(flattened)))

    def test_legs_and_glutes_share_a_day(self):
        cycle = build_mesocycle(
            muscle_states=[_state("legs"), _state("glutes")],
            strength_entries=[],
            weeks=2,
            days_per_week=2,
        )
        focuses = [set(day.focus) for week in cycle.weeks for day in week.sessions]
        self.assertTrue(any("legs" in f and "glutes" in f for f in focuses))


def _group(muscle):
    for group, members in MUSCLE_GROUPS.items():
        if muscle in members:
            return group
    return "core"


class ReadmeOrientationTests(unittest.TestCase):
    def test_snapshot_dict_input_accepted(self):
        cycle = build_mesocycle(
            muscle_states={"muscles": [_state("chest")]},
            weeks=2,
            days_per_week=1,
        )
        self.assertIn("chest", cycle.focus)

    def test_state_mapping_input_accepted(self):
        cycle = build_mesocycle(
            muscle_states={"chest": _state("chest")},
            weeks=2,
            days_per_week=1,
        )
        self.assertIn("chest", cycle.focus)


if __name__ == "__main__":
    unittest.main()
