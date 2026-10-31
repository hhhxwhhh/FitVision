"""Deterministic synthetic training-history generation.

Pure Python (no Django imports) so the generator can be unit-tested with the
standard library and reused by the ``seed_demo_history`` management command.

The generator produces realistic, reproducible workout sessions for a demo
user: a stable weekly habit, a rotating muscle focus, gradual progression in
form scores, and plausible calories/duration. Management commands map these
specs onto the ORM models.
"""

from __future__ import annotations

import random
from datetime import date, datetime, time, timedelta

# Muscle focus rotates session by session so the demo history looks varied.
DEFAULT_FOCUS_ROTATION = (
    "legs",
    "chest",
    "back",
    "abs",
    "full_body",
    "shoulders",
    "glutes",
    "arms",
)

# Consistent weekly habits (Monday = 0). Ad-hoc patterns are sampled when the
# requested frequency is not in this table.
WEEKDAY_PATTERNS = {
    1: (2,),
    2: (1, 4),
    3: (0, 2, 4),
    4: (0, 2, 4, 5),
    5: (0, 1, 3, 4, 5),
    6: (0, 1, 2, 3, 4, 5),
}

DEFAULT_START_HOURS = (7, 12, 18, 19, 20)
DEFAULT_START_MINUTES = (0, 10, 15, 30, 45)


def _weekday_pattern(days_per_week: int, rng: random.Random) -> tuple[int, ...]:
    if days_per_week in WEEKDAY_PATTERNS:
        return WEEKDAY_PATTERNS[days_per_week]
    count = max(1, min(days_per_week, 7))
    return tuple(sorted(rng.sample(range(7), count)))


def _build_session(
    rng: random.Random,
    catalog: list[dict],
    day: date,
    week: int,
    weeks: int,
    focus: str,
    min_exercises: int,
    max_exercises: int,
) -> dict | None:
    pool = [item for item in catalog if item.get("target_muscle") == focus]
    if len(pool) < min_exercises:
        pool = list(catalog)
    if not pool:
        return None

    count = rng.randint(min(min_exercises, len(pool)), min(max_exercises, len(pool)))
    chosen = rng.sample(pool, count)

    # Form scores improve from the first week to the last.
    week_ratio = (weeks - 1 - week) / max(weeks - 1, 1)
    base_form = 70.0 + 14.0 * week_ratio

    start = datetime.combine(
        day,
        time(
            hour=rng.choice(DEFAULT_START_HOURS),
            minute=rng.choice(DEFAULT_START_MINUTES),
        ),
    )

    exercises = []
    cursor = start
    total_calories = 0.0

    for index, item in enumerate(chosen):
        sets = rng.randint(3, 4)
        base_reps = int(item.get("default_reps") or 10)
        start_reps = max(4, base_reps + rng.randint(-2, 2))
        # Reps typically fade across sets as fatigue accumulates.
        reps = [
            max(4, start_reps - step - (1 if rng.random() < 0.25 else 0))
            for step in range(sets)
        ]
        form = max(35.0, min(99.0, base_form + rng.uniform(-6, 6) - index * 0.8))

        # Cap the work portion of a set (high-rep moves like high knees would
        # otherwise produce implausibly long, high-calorie exercises).
        average_reps = sum(reps) / sets
        work_per_set = min(average_reps * 3.0, 75.0)
        duration_seconds = min(int(sets * (work_per_set + 45.0)), 720)

        rate = float(item.get("calories_burned") or 5.0)
        calories = round(rate * (duration_seconds / 60.0), 1)

        weight = 0.0
        if item.get("equipment") in ("dumbbell", "barbell", "kettlebell"):
            weight = float(rng.choice([10, 15, 20, 25, 30]))

        exercises.append(
            {
                "name": item["name"],
                "sets": sets,
                "reps": reps,
                "weight": weight,
                "duration_seconds": duration_seconds,
                "form_score": round(form, 1),
                "calories_burned": calories,
            }
        )

        total_calories += calories
        cursor += timedelta(seconds=duration_seconds + 60)

    completed = rng.random() < 0.9
    form_scores = [entry["form_score"] for entry in exercises]
    average_form = sum(form_scores) / len(form_scores) if form_scores else 0.0
    performance = round(average_form * (1.0 if completed else 0.6), 1)
    end_time = cursor if completed else start + timedelta(minutes=12)

    return {
        "date": day,
        "start_time": start,
        "end_time": end_time,
        "duration_minutes": max(1, int((end_time - start).total_seconds() // 60)),
        "completed": completed,
        "performance_score": performance,
        "calories_burned": round(total_calories, 1),
        "focus": focus,
        "exercises": exercises,
    }


def generate_training_history(
    catalog: list[dict],
    seed: int = 42,
    weeks: int = 8,
    days_per_week: int = 4,
    end_date: date | None = None,
    adherence: float = 0.82,
    min_exercises: int = 3,
    max_exercises: int = 6,
) -> list[dict]:
    """Generate reproducible workout sessions ending at ``end_date``.

    ``catalog`` items must provide ``name``, ``target_muscle`` and optionally
    ``equipment``, ``calories_burned`` and ``default_reps``.
    """
    if not catalog or weeks <= 0 or days_per_week <= 0:
        return []

    rng = random.Random(seed)
    end = end_date or date.today()
    pattern = _weekday_pattern(days_per_week, rng)

    sessions: list[dict] = []
    session_index = 0

    for week in range(weeks - 1, -1, -1):
        week_monday = end - timedelta(days=end.weekday()) - timedelta(weeks=week)
        for weekday in pattern:
            day = week_monday + timedelta(days=weekday)
            if day > end:
                continue
            if rng.random() > adherence:
                continue

            focus = DEFAULT_FOCUS_ROTATION[session_index % len(DEFAULT_FOCUS_ROTATION)]
            session = _build_session(
                rng, catalog, day, week, weeks, focus, min_exercises, max_exercises
            )
            if session:
                sessions.append(session)
                session_index += 1

    sessions.sort(key=lambda item: item["start_time"])
    return sessions


def longest_streak(days: list[date]) -> int:
    """Longest run of consecutive calendar days."""
    ordered = sorted(set(days))
    if not ordered:
        return 0
    best = current = 1
    for previous, current_day in zip(ordered, ordered[1:]):
        if (current_day - previous).days == 1:
            current += 1
            best = max(best, current)
        else:
            current = 1
    return best


def summarize_history(sessions: list[dict], today: date | None = None) -> dict:
    """Aggregate generated sessions into the numbers the dashboard needs."""
    valid = [item for item in sessions if item.get("exercises")]
    if not valid:
        return {
            "sessions": 0,
            "training_days": 0,
            "total_minutes": 0,
            "total_calories": 0.0,
            "average_form": 0.0,
            "longest_streak": 0,
            "weekly_sessions": 0,
            "monthly_sessions": 0,
        }

    days = sorted({item["start_time"].date() for item in valid})
    total_minutes = sum(item["duration_minutes"] for item in valid)
    total_calories = round(sum(item["calories_burned"] for item in valid), 1)
    form_scores = [entry["form_score"] for item in valid for entry in item["exercises"]]
    average_form = round(sum(form_scores) / len(form_scores), 1) if form_scores else 0.0

    reference = today or days[-1]
    week_start = reference - timedelta(days=reference.weekday())
    weekly = sum(1 for day in days if week_start <= day <= week_start + timedelta(days=6))
    monthly = sum(1 for day in days if day.year == reference.year and day.month == reference.month)

    return {
        "sessions": len(valid),
        "training_days": len(days),
        "total_minutes": total_minutes,
        "total_calories": total_calories,
        "average_form": average_form,
        "longest_streak": longest_streak(days),
        "weekly_sessions": weekly,
        "monthly_sessions": monthly,
    }
