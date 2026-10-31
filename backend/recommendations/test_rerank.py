"""Unit tests for the MMR re-ranking algorithm.

These tests intentionally avoid Django so they can run both with
``python manage.py test`` (CI) and directly via ``python -m unittest``.
"""

import unittest
from types import SimpleNamespace

from .rerank import exercise_similarity, mmr_rerank


def _ex(muscle="", equipment="", difficulty="", tags=None):
    return SimpleNamespace(
        target_muscle=muscle, equipment=equipment, difficulty=difficulty, tags=tags or []
    )


class ExerciseSimilarityTests(unittest.TestCase):
    def test_identical_attributes_are_highly_similar(self):
        a = _ex("chest", "none", "beginner", ["push"])
        b = _ex("chest", "none", "beginner", ["push"])
        self.assertAlmostEqual(exercise_similarity(a, b), 1.0)

    def test_same_object_is_fully_similar(self):
        a = _ex("chest")
        self.assertEqual(exercise_similarity(a, a), 1.0)

    def test_different_muscle_lowers_similarity(self):
        a = _ex("chest", "none", "beginner", ["push"])
        b = _ex("legs", "none", "beginner", ["squat"])
        self.assertLess(exercise_similarity(a, b), 0.3)

    def test_shared_tags_increase_similarity(self):
        base = dict(muscle="chest", equipment="none", difficulty="beginner")
        a = _ex(tags=["push", "chest"], **base)
        b = _ex(tags=["push"], **base)
        c = _ex(tags=["pull"], **base)
        self.assertGreater(exercise_similarity(a, b), exercise_similarity(a, c))


class MmrRerankTests(unittest.TestCase):
    def setUp(self):
        self.a = _ex("chest", "none", "beginner", ["push"])
        self.b = _ex("chest", "none", "beginner", ["push"])  # near-duplicate of a
        self.c = _ex("legs", "none", "beginner", ["squat"])
        self.candidates = [
            {"ex": self.a, "score": 0.9},
            {"ex": self.b, "score": 0.85},
            {"ex": self.c, "score": 0.8},
        ]

    def test_empty_or_non_positive_limit(self):
        self.assertEqual(mmr_rerank([], 5), [])
        self.assertEqual(mmr_rerank(self.candidates, 0), [])
        self.assertEqual(mmr_rerank(self.candidates, -1), [])

    def test_limit_is_respected(self):
        result = mmr_rerank(self.candidates, 2)
        self.assertEqual(len(result), 2)

    def test_first_item_is_highest_relevance(self):
        result = mmr_rerank(self.candidates, 3)
        self.assertIs(result[0]["ex"], self.a)

    def test_promotes_diversity_over_redundancy(self):
        result = mmr_rerank(self.candidates, 3, lambda_=0.6)
        # The diverse leg exercise should outrank the near-duplicate chest one.
        self.assertIs(result[1]["ex"], self.c)
        self.assertIs(result[2]["ex"], self.b)

    def test_pure_relevance_when_lambda_is_one(self):
        result = mmr_rerank(self.candidates, 3, lambda_=1.0)
        self.assertEqual([item["ex"] for item in result], [self.a, self.b, self.c])

    def test_does_not_mutate_input(self):
        snapshot = [item["score"] for item in self.candidates]
        mmr_rerank(self.candidates, 3)
        self.assertEqual([item["score"] for item in self.candidates], snapshot)
        self.assertEqual(len(self.candidates), 3)


if __name__ == "__main__":
    unittest.main()
