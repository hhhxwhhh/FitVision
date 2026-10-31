"""Unit tests for the synthetic training-history generator.

Runs without Django: ``python -m unittest utils.test_demo_data``.
"""

import unittest
from datetime import date

from .demo_data import (
    build_persona,
    generate_population,
    generate_training_history,
    longest_streak,
    summarize_history,
    summarize_population,
    week_load_factor,
)


def _catalog():
    return [
        {
            "name": f"legs-{i}",
            "target_muscle": "legs",
            "equipment": "none",
            "calories_burned": 6.0,
            "default_reps": 12,
        }
        for i in range(5)
    ] + [
        {
            "name": f"chest-{i}",
            "target_muscle": "chest",
            "equipment": "dumbbell",
            "calories_burned": 5.0,
            "default_reps": 10,
        }
        for i in range(5)
    ]


END = date(2026, 10, 31)


class GenerateTrainingHistoryTests(unittest.TestCase):
    def test_empty_catalog_returns_nothing(self):
        self.assertEqual(generate_training_history([], end_date=END), [])

    def test_is_deterministic_for_a_seed(self):
        first = generate_training_history(_catalog(), seed=7, weeks=4, end_date=END)
        second = generate_training_history(_catalog(), seed=7, weeks=4, end_date=END)
        self.assertEqual(
            [item["start_time"] for item in first],
            [item["start_time"] for item in second],
        )
        self.assertEqual(first, second)

    def test_never_emits_sessions_in_the_future(self):
        sessions = generate_training_history(_catalog(), seed=3, weeks=6, end_date=END)
        self.assertTrue(sessions)
        for session in sessions:
            self.assertLessEqual(session["date"], END)

    def test_exercises_come_from_catalog_and_respect_bounds(self):
        names = {entry["name"] for entry in _catalog()}
        sessions = generate_training_history(
            _catalog(), seed=11, weeks=4, days_per_week=3, end_date=END,
            min_exercises=3, max_exercises=5,
        )
        self.assertTrue(sessions)
        for session in sessions:
            self.assertGreaterEqual(len(session["exercises"]), 3)
            self.assertLessEqual(len(session["exercises"]), 5)
            for entry in session["exercises"]:
                self.assertIn(entry["name"], names)
                self.assertGreater(entry["sets"], 0)
                self.assertTrue(all(rep > 0 for rep in entry["reps"]))
                self.assertGreaterEqual(entry["form_score"], 0.0)
                self.assertLessEqual(entry["form_score"], 100.0)

    def test_sessions_are_sorted_by_start_time(self):
        sessions = generate_training_history(_catalog(), seed=5, weeks=5, end_date=END)
        starts = [item["start_time"] for item in sessions]
        self.assertEqual(starts, sorted(starts))

    def test_performance_score_uses_the_zero_to_five_scale(self):
        """成长 XP 里按 performance_score × 4 折算质量加成，所以必须是 0-5 分制。"""
        sessions = generate_training_history(_catalog(), seed=13, weeks=4, end_date=END)
        self.assertTrue(sessions)
        for session in sessions:
            self.assertGreaterEqual(session["performance_score"], 0.0)
            self.assertLessEqual(session["performance_score"], 5.0)


class PeriodizationTests(unittest.TestCase):
    def test_four_week_cycle_rampa_up_then_deloads(self):
        # week=weeks-1 是最旧的一周，week=0 是当前周
        ramp = [week_load_factor(week=7 - k, weeks=8) for k in range(8)]
        self.assertEqual(ramp[0], 0.92)
        self.assertGreater(ramp[1], ramp[0])
        self.assertGreater(ramp[2], ramp[1])
        self.assertLess(ramp[3], ramp[2])  # 第 4 周减量

    def test_later_blocks_carry_more_load(self):
        self.assertGreater(week_load_factor(week=3, weeks=8), week_load_factor(week=7, weeks=8))

    def test_the_factor_stays_in_a_sane_band(self):
        for weeks in (1, 2, 4, 8, 16, 24):
            for week in range(weeks):
                factor = week_load_factor(week=week, weeks=weeks)
                self.assertGreaterEqual(factor, 0.6)
                self.assertLessEqual(factor, 1.3)

    def test_deload_weeks_are_shorter_than_build_weeks(self):
        sessions = generate_training_history(_catalog(), seed=21, weeks=8, end_date=END)
        minutes_by_week = {}
        for session in sessions:
            key = session["date"].isocalendar()[1]
            minutes_by_week.setdefault(key, []).append(session["duration_minutes"])

        averages = {key: sum(v) / len(v) for key, v in minutes_by_week.items()}
        self.assertGreater(len(averages), 1)
        self.assertGreater(max(averages.values()), min(averages.values()))

    def test_periodization_can_be_disabled(self):
        flat = generate_training_history(
            _catalog(), seed=31, weeks=8, end_date=END, periodization=False
        )
        waved = generate_training_history(_catalog(), seed=31, weeks=8, end_date=END)
        self.assertNotEqual(
            [item["duration_minutes"] for item in flat],
            [item["duration_minutes"] for item in waved],
        )


class SummarizeHistoryTests(unittest.TestCase):
    def test_empty_summary(self):
        summary = summarize_history([])
        self.assertEqual(summary["sessions"], 0)
        self.assertEqual(summary["training_days"], 0)
        self.assertEqual(summary["longest_streak"], 0)

    def test_summary_matches_generated_sessions(self):
        sessions = generate_training_history(_catalog(), seed=9, weeks=6, end_date=END)
        summary = summarize_history(sessions, today=END)

        self.assertEqual(summary["sessions"], len(sessions))
        self.assertEqual(
            summary["total_minutes"], sum(item["duration_minutes"] for item in sessions)
        )
        self.assertAlmostEqual(
            summary["total_calories"],
            round(sum(item["calories_burned"] for item in sessions), 1),
        )
        self.assertGreater(summary["training_days"], 0)
        self.assertGreaterEqual(summary["longest_streak"], 1)
        self.assertLessEqual(summary["weekly_sessions"], 7)


class LongestStreakTests(unittest.TestCase):
    def test_counts_consecutive_days(self):
        days = [
            date(2026, 10, 1),
            date(2026, 10, 2),
            date(2026, 10, 3),
            date(2026, 10, 6),
            date(2026, 10, 7),
        ]
        self.assertEqual(longest_streak(days), 3)

    def test_handles_empty_and_duplicates(self):
        self.assertEqual(longest_streak([]), 0)
        self.assertEqual(longest_streak([date(2026, 10, 1), date(2026, 10, 1)]), 1)


class PopulationTests(unittest.TestCase):
    def test_build_persona_is_deterministic_and_balanced(self):
        first = build_persona(0)
        self.assertEqual(build_persona(0), first)
        self.assertEqual(first["username"], "trainee01")

        levels = {build_persona(i)["level"] for i in range(3)}
        self.assertEqual(len(levels), 3)

    def test_persona_level_drives_training_frequency(self):
        beginner = build_persona(0)
        advanced = build_persona(2)
        self.assertEqual(beginner["level"], "beginner")
        self.assertEqual(advanced["level"], "advanced")
        self.assertLess(beginner["days_per_week"], advanced["days_per_week"])
        self.assertLess(beginner["adherence"], advanced["adherence"])

    def test_generate_population_is_reproducible(self):
        catalog = _catalog()
        end = date(2026, 10, 31)
        first = generate_population(catalog, users=6, weeks=4, end_date=end)
        second = generate_population(catalog, users=6, weeks=4, end_date=end)
        self.assertEqual(first, second)

    def test_population_summaries_aggregate_every_user(self):
        population = generate_population(_catalog(), users=6, weeks=4, end_date=date(2026, 10, 31))
        stats = summarize_population(population)

        self.assertEqual(stats["users"], 6)
        self.assertEqual(stats["sessions"], sum(len(p["sessions"]) for p in population))
        self.assertGreater(stats["sessions"], 0)
        self.assertGreater(stats["minutes"], 0)
        self.assertGreater(stats["average_form"], 0)

    def test_empty_inputs_are_handled(self):
        self.assertEqual(generate_population([], users=3), [])
        self.assertEqual(generate_population(_catalog(), users=0), [])
        self.assertEqual(summarize_population([])["users"], 0)


if __name__ == "__main__":
    unittest.main()
