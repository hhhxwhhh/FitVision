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


def week_load_factor(week: int, weeks: int, cycle: int = 4) -> float:
    """周期化负荷系数：4 周一循环，前 3 周渐进超负荷，第 4 周减量（deload）。

    这样生成的演示数据在负荷模型里才有意义 —— 急性/慢性负荷比会随周期起伏，
    减量周的 TSB 会转正，而不是一条永远水平的直线。
    """
    if weeks <= 0:
        return 1.0
    index_from_start = weeks - 1 - week  # 0 = 最旧的一周
    phase = index_from_start % cycle
    block = index_from_start // cycle

    if phase == cycle - 1:
        factor = 0.68  # 减量周：容量明显下调
    else:
        factor = 0.92 + 0.08 * phase  # 0.92 / 1.00 / 1.08

    # 每个周期整体再抬一点点，形成长期渐进超负荷
    return round(min(1.3, factor + 0.02 * block), 3)


def _build_session(
    rng: random.Random,
    catalog: list[dict],
    day: date,
    week: int,
    weeks: int,
    focus: str,
    min_exercises: int,
    max_exercises: int,
    base_form: float = 70.0,
    form_growth: float = 14.0,
    load_factor: float = 1.0,
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
    base_form = base_form + form_growth * week_ratio

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
        # 组数随周期化系数伸缩：减量周 2 组，峰值周 4-5 组
        sets = max(2, int(round(rng.randint(3, 4) * load_factor)))
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
        duration_seconds = min(int(sets * (work_per_set + 45.0) * load_factor), 720)

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
    # `UserTrainingSession.performance_score` 是 0-5 分制（成长 XP 里按 ×4 折算成
    # 0-20 分的质量加成），所以这里要把 0-100 的动作平均评分换算过去。
    performance = round(min(5.0, average_form / 20.0) * (1.0 if completed else 0.6), 2)
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
    base_form: float = 70.0,
    form_growth: float = 14.0,
    periodization: bool = True,
) -> list[dict]:
    """Generate reproducible workout sessions ending at ``end_date``.

    ``catalog`` items must provide ``name``, ``target_muscle`` and optionally
    ``equipment``, ``calories_burned`` and ``default_reps``.

    ``periodization=True``（默认）按 4 周一个小周期安排负荷：前 3 周渐进超负荷，
    第 4 周减量。关掉它会退回"每周都一样"的旧行为。
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
                rng,
                catalog,
                day,
                week,
                weeks,
                focus,
                min_exercises,
                max_exercises,
                base_form,
                form_growth,
                week_load_factor(week, weeks) if periodization else 1.0,
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


# ---------------------------------------------------------------------------
# Population generation: many users with different profiles, used to give the
# recommender enough signal to train and evaluate on.
# ---------------------------------------------------------------------------

FITNESS_LEVELS = ("beginner", "intermediate", "advanced")

LEVEL_PROFILE = {
    # level: (days per week, adherence, base form score, form growth per week)
    "beginner": (2, 0.72, 62.0, 1.6),
    "intermediate": (3, 0.84, 72.0, 1.1),
    "advanced": (4, 0.92, 82.0, 0.7),
}

GOAL_FOCUS_BIAS = {
    "weight_loss": ("full_body", "abs", "legs"),
    "muscle_gain": ("chest", "back", "arms"),
    "endurance": ("full_body", "legs", "glutes"),
    "flexibility": ("abs", "back", "shoulders"),
}

DEFAULT_GOALS = tuple(GOAL_FOCUS_BIAS)


def build_persona(index: int, goals: tuple[str, ...] = DEFAULT_GOALS) -> dict:
    """Deterministic persona for the nth synthetic user.

    Spreading levels and goals evenly keeps the dataset balanced instead of
    clustering everyone around one profile.
    """
    level = FITNESS_LEVELS[index % len(FITNESS_LEVELS)]
    goal = goals[index % len(goals)] if goals else DEFAULT_GOALS[0]
    days, adherence, base_form, growth = LEVEL_PROFILE[level]
    return {
        "username": f"trainee{index + 1:02d}",
        "level": level,
        "goal": goal,
        "days_per_week": days,
        "adherence": adherence,
        "base_form": base_form,
        "form_growth": growth,
        "preferred_focus": GOAL_FOCUS_BIAS.get(goal, DEFAULT_FOCUS_ROTATION[:3]),
    }


def generate_population(
    catalog: list[dict],
    users: int = 12,
    seed: int = 7,
    weeks: int = 6,
    end_date: date | None = None,
) -> list[dict]:
    """Generate a balanced multi-user dataset for training and evaluation.

    Each entry carries the persona plus its own session list, so callers can
    seed users, histories and interactions consistently.
    """
    if not catalog or users <= 0 or weeks <= 0:
        return []

    end = end_date or date.today()
    population: list[dict] = []

    for index in range(users):
        persona = build_persona(index)
        sessions = generate_training_history(
            catalog,
            seed=seed + index * 101,
            weeks=weeks,
            days_per_week=persona["days_per_week"],
            end_date=end,
            adherence=persona["adherence"],
            base_form=persona["base_form"],
            form_growth=persona["form_growth"] * weeks,
        )
        population.append(
            {
                **persona,
                "sessions": sessions,
                "summary": summarize_history(sessions, today=end),
            }
        )

    return population


def summarize_population(population: list[dict]) -> dict:
    """Headline counters for a generated population."""
    if not population:
        return {"users": 0, "sessions": 0, "minutes": 0, "calories": 0.0, "average_form": 0.0}

    sessions = sum(len(person["sessions"]) for person in population)
    minutes = sum(person["summary"].get("total_minutes", 0) or 0 for person in population)
    calories = sum(person["summary"].get("total_calories", 0.0) or 0.0 for person in population)
    forms = [
        person["summary"].get("average_form", 0.0) or 0.0
        for person in population
        if person["summary"].get("sessions")
    ]
    return {
        "users": len(population),
        "sessions": sessions,
        "minutes": minutes,
        "calories": round(calories, 1),
        "average_form": round(sum(forms) / len(forms), 1) if forms else 0.0,
        "levels": {
            level: sum(1 for person in population if person["level"] == level)
            for level in FITNESS_LEVELS
        },
        "goals": {
            goal: sum(1 for person in population if person["goal"] == goal)
            for goal in {person["goal"] for person in population}
        },
    }
