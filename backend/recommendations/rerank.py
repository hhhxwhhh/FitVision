"""Diversity-aware re-ranking for the hybrid recommender.

Pure functions (no Django imports) so the ranking algorithm can be unit-tested
in isolation with the standard library ``unittest`` runner.

Implements Maximal Marginal Relevance (MMR): greedily select the candidate that
maximises ``lambda * relevance - (1 - lambda) * redundancy``, where relevance is
the candidate's hybrid score and redundancy is its maximum similarity to the
items already selected. This replaces the older fixed per-muscle penalty with a
principled relevance/diversity trade-off.
"""

# Weights for the hand-crafted exercise similarity signal.
_MUSCLE_WEIGHT = 0.5
_TAG_WEIGHT = 0.3
_EQUIPMENT_WEIGHT = 0.1
_DIFFICULTY_WEIGHT = 0.1


def _attr(exercise, name, default=""):
    value = getattr(exercise, name, None)
    return value if value else default


def _tags(exercise):
    return set(getattr(exercise, "tags", None) or [])


def _jaccard(a, b):
    union = a | b
    if not union:
        return 0.0
    return len(a & b) / len(union)


def exercise_similarity(a, b):
    """Similarity in [0, 1] between two exercises based on shared attributes."""
    if a is b:
        return 1.0

    muscle_a, muscle_b = _attr(a, "target_muscle"), _attr(b, "target_muscle")
    muscle = 1.0 if muscle_a and muscle_a == muscle_b else 0.0

    equip_a, equip_b = _attr(a, "equipment"), _attr(b, "equipment")
    equipment = 1.0 if equip_a and equip_a == equip_b else 0.0

    diff_a, diff_b = _attr(a, "difficulty"), _attr(b, "difficulty")
    difficulty = 1.0 if diff_a and diff_a == diff_b else 0.0

    tags = _jaccard(_tags(a), _tags(b))

    return (
        _MUSCLE_WEIGHT * muscle
        + _TAG_WEIGHT * tags
        + _EQUIPMENT_WEIGHT * equipment
        + _DIFFICULTY_WEIGHT * difficulty
    )


def mmr_rerank(candidates, limit, lambda_=0.7, max_scan=40):
    """Re-order ``candidates`` (dicts with ``ex`` and ``score``) using MMR.

    Returns a new list of at most ``limit`` candidate dicts; the input list and
    the candidate scores are left untouched.
    """
    if not candidates or limit <= 0:
        return []

    pool = list(candidates)
    selected = []

    while pool and len(selected) < limit:
        best_idx = 0
        best_value = float("-inf")

        for idx, item in enumerate(pool[:max_scan]):
            relevance = item.get("score", 0.0) or 0.0
            if not selected:
                value = relevance
            else:
                redundancy = max(
                    exercise_similarity(item["ex"], chosen["ex"]) for chosen in selected
                )
                value = lambda_ * relevance - (1 - lambda_) * redundancy

            if value > best_value:
                best_value = value
                best_idx = idx

        selected.append(pool.pop(best_idx))

    return selected
