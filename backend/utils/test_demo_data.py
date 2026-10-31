"""Unit tests for the synthetic training-history generator.

Runs without Django: ``python -m unittest utils.test_demo_data``.
"""

import unittest
from datetime import date

from .demo_data import longest_streak, generate_training_history, summarize_history


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


if __name__ == "__main__":
    unittest.main()
