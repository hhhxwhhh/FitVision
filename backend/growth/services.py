"""成长体系的核心计算逻辑。

设计原则：
- 训练会话与动作记录是事实来源，XP / 等级 / 连续天数都由它们推导。
- 所有发奖入口使用 XPEvent 唯一约束做幂等，重复保存训练会话不会重复加经验。
- 每日任务与周目标只缓存展示进度，读取时重新计算，避免缓存漂移。
"""

from __future__ import annotations

from datetime import date, datetime, time, timedelta
from typing import Iterable

from django.db import transaction
from django.db.models import Avg, Max, Sum
from django.utils import timezone

from training.models import UserTrainingExerciseRecord, UserTrainingSession
from users.models import UserStats
from utils.readiness import HISTORY_DAYS, DailyLoad, load_curve, readiness_report, session_load
from utils.recovery import MUSCLE_ORDER, MuscleWork, RecoverySnapshot, muscle_recovery
from utils.strength import (
    build_sets,
    estimate_session_e1rm,
    next_prescription,
    strength_summary,
)

from .models import (
    Achievement,
    Challenge,
    PersonalRecord,
    UserAchievement,
    UserChallenge,
    UserDailyQuest,
    UserProgress,
    WeeklyGoal,
    XPEvent,
)

# 每级升级所需经验 = 100 + (当前等级 - 1) * 50
LEVEL_STEP = 50
LEVEL_BASE = 100

LEVEL_TITLES = [
    (15, "传奇"),
    (10, "精英"),
    (7, "达人"),
    (5, "进阶"),
    (3, "学徒"),
    (1, "新手"),
]

QUEST_POOL = [
    {
        "code": "daily_session",
        "title": "完成一次训练",
        "description": "完成 1 次训练会话",
        "metric": "sessions",
        "target": 1,
        "xp_reward": 30,
    },
    {
        "code": "daily_minutes",
        "title": "持续燃烧",
        "description": "今日累计训练 20 分钟",
        "metric": "minutes",
        "target": 20,
        "xp_reward": 30,
    },
    {
        "code": "daily_exercises",
        "title": "动作组合",
        "description": "今日完成 3 个不同动作",
        "metric": "distinct_exercises",
        "target": 3,
        "xp_reward": 25,
    },
    {
        "code": "daily_quality",
        "title": "质量优先",
        "description": "单个动作评分达到 85 分",
        "metric": "best_form_score",
        "target": 85,
        "xp_reward": 35,
    },
    {
        "code": "daily_calories",
        "title": "能量消耗",
        "description": "今日消耗 200 千卡",
        "metric": "calories",
        "target": 200,
        "xp_reward": 25,
    },
    {
        "code": "daily_volume",
        "title": "容量冲刺",
        "description": "今日累计训练容量达到 1000",
        "metric": "volume",
        "target": 1000,
        "xp_reward": 30,
    },
]

WEEKLY_GOAL_XP = 80


# ---------------------------------------------------------------------------
# 等级
# ---------------------------------------------------------------------------
def xp_for_level(level: int) -> int:
    """升到指定等级所需的累计经验。"""
    level = max(1, int(level))
    return 25 * (level - 1) * (level + 2)


def level_from_xp(xp: int) -> int:
    level = 1
    while xp >= xp_for_level(level + 1):
        level += 1
        if level > 999:
            break
    return level


def level_title(level: int) -> str:
    for threshold, title in LEVEL_TITLES:
        if level >= threshold:
            return title
    return "新手"


def level_progress(xp: int) -> dict:
    level = level_from_xp(xp)
    current_floor = xp_for_level(level)
    next_floor = xp_for_level(level + 1)
    span = max(1, next_floor - current_floor)
    into_level = max(0, xp - current_floor)
    return {
        "level": level,
        "title": level_title(level),
        "xp": xp,
        "xp_into_level": into_level,
        "xp_next_level": next_floor - xp,
        "level_span": span,
        "progress_percent": round(min(100.0, into_level / span * 100), 1),
    }


# ---------------------------------------------------------------------------
# 基础数据
# ---------------------------------------------------------------------------
def _completed_sessions(user):
    return UserTrainingSession.objects.filter(user=user, is_completed=True)


def _minutes(session: UserTrainingSession) -> float:
    if not session.end_time or not session.start_time:
        return 0.0
    return max(0.0, (session.end_time - session.start_time).total_seconds() / 60)


def _numeric(values: Iterable) -> list[float]:
    parsed: list[float] = []
    for value in values or []:
        text = str(value).strip()
        if not text:
            continue
        try:
            parsed.append(float(text))
        except (TypeError, ValueError):
            continue
    return parsed


def _record_volume(record: UserTrainingExerciseRecord) -> float:
    weights = _numeric(record.weights_used)
    reps = _numeric(record.reps_completed)
    if weights and len(weights) == len(reps):
        return sum(weight * rep for weight, rep in zip(weights, reps))
    if reps:
        # 自重动作按 20kg 等效负荷折算，与推荐模块保持一致。
        return sum(reps) * 20.0
    return 0.0


def streaks_from_dates(dates: Iterable[date]) -> tuple[int, int]:
    """返回 (当前连续天数, 历史最长连续天数)。

    当天尚未训练时，从昨天开始计算当前连续天数，避免白天登录就显示中断。
    """
    ordered = sorted(set(dates))
    if not ordered:
        return 0, 0

    longest = 1
    run = 1
    for previous, current in zip(ordered, ordered[1:]):
        if current - previous == timedelta(days=1):
            run += 1
            longest = max(longest, run)
        else:
            run = 1

    date_set = set(ordered)
    cursor = timezone.localdate()
    if cursor not in date_set:
        cursor -= timedelta(days=1)
    current_streak = 0
    while cursor in date_set:
        current_streak += 1
        cursor -= timedelta(days=1)

    return current_streak, longest


def _training_dates(user) -> set[date]:
    return set(
        _completed_sessions(user).values_list("start_time__date", flat=True).distinct()
    )


def week_start_for(day: date | None = None) -> date:
    day = day or timezone.localdate()
    return day - timedelta(days=day.weekday())


def build_metrics(user) -> dict:
    """汇总成就判定所需的全部指标。"""
    sessions = _completed_sessions(user)
    session_count = sessions.count()

    total_minutes = 0.0
    weekly_dates: set[date] = set()
    monday = week_start_for()
    for start_time, end_time in sessions.values_list("start_time", "end_time"):
        if end_time and start_time:
            total_minutes += max(
                0.0, (end_time - start_time).total_seconds() / 60
            )
        if start_time:
            local_day = timezone.localtime(start_time).date()
            if local_day >= monday:
                weekly_dates.add(local_day)

    dates = _training_dates(user)
    current_streak, longest_streak = streaks_from_dates(dates)

    records = UserTrainingExerciseRecord.objects.filter(
        session__user=user, session__is_completed=True
    )
    best_form = float(records.aggregate(value=Max("form_score"))["value"] or 0)
    calories = float(
        sessions.aggregate(value=Sum("calories_burned"))["value"] or 0
    )
    distinct_exercises = records.values("exercise_id").distinct().count()
    personal_records = PersonalRecord.objects.filter(user=user).count()
    total_volume = 0.0
    for record in records.only("weights_used", "reps_completed"):
        total_volume += _record_volume(record)

    early_sessions = sessions.filter(start_time__hour__lt=7).count()
    night_sessions = sessions.filter(start_time__hour__gte=22).count()
    challenges_claimed = UserChallenge.objects.filter(
        user=user, claimed_at__isnull=False
    ).count()
    progress, _ = UserProgress.objects.get_or_create(user=user)

    return {
        "sessions": session_count,
        "streak": current_streak,
        "longest_streak": longest_streak,
        "training_days": len(dates),
        "minutes": round(total_minutes, 1),
        "calories": round(calories, 1),
        "best_form_score": best_form,
        "personal_records": personal_records,
        "total_volume": round(total_volume, 1),
        "distinct_exercises": distinct_exercises,
        "weekly_days": len(weekly_dates),
        "early_sessions": early_sessions,
        "night_sessions": night_sessions,
        "challenges_claimed": challenges_claimed,
        "level": progress.level,
    }


# ---------------------------------------------------------------------------
# XP 与成长进度
# ---------------------------------------------------------------------------
def award_xp(user, source: str, reference_id: int, amount: int, note: str = ""):
    """幂等地发放经验；返回 (XPEvent, created)。"""
    amount = max(0, int(amount))
    with transaction.atomic():
        event, created = XPEvent.objects.get_or_create(
            user=user,
            source=source,
            reference_id=reference_id,
            defaults={"amount": amount, "note": note},
        )
        if not created:
            return event, False

        progress, _ = UserProgress.objects.select_for_update().get_or_create(user=user)
        progress.xp += amount
        progress.level = level_from_xp(progress.xp)
        progress.save(update_fields=["xp", "level", "updated_at"])
        return event, True


def session_xp(session: UserTrainingSession, current_streak: int) -> int:
    minutes = _minutes(session)
    base = 20
    duration_bonus = min(30, int(minutes / 2))
    quality_bonus = min(20, int(round(float(session.performance_score or 0) * 4)))
    streak_bonus = min(20, current_streak * 2)
    return base + duration_bonus + quality_bonus + streak_bonus


def refresh_user_stats(user) -> UserStats:
    """从训练会话重新计算 UserStats，修复历史统计不更新的问题。"""
    sessions = _completed_sessions(user)
    dates = _training_dates(user)
    current_streak, longest_streak = streaks_from_dates(dates)

    total_seconds = 0.0
    for start_time, end_time in sessions.values_list("start_time", "end_time"):
        if start_time and end_time:
            total_seconds += max(0.0, (end_time - start_time).total_seconds())

    today = timezone.localdate()
    monday = week_start_for(today)
    weekly_count = sessions.filter(start_time__date__gte=monday).count()
    monthly_count = sessions.filter(
        start_time__year=today.year, start_time__month=today.month
    ).count()
    best_form = UserTrainingExerciseRecord.objects.filter(
        session__user=user, session__is_completed=True
    ).aggregate(value=Max("form_score"))["value"] or 0

    stats, _ = UserStats.objects.get_or_create(user=user)
    stats.total_trainings = sessions.count()
    stats.total_training_days = len(dates)
    stats.total_training_time = int(total_seconds // 60)
    stats.total_calories_burned = float(
        sessions.aggregate(value=Sum("calories_burned"))["value"] or 0
    )
    stats.best_accuracy_score = float(best_form)
    stats.longest_training_streak = max(
        stats.longest_training_streak, longest_streak, current_streak
    )
    stats.weekly_trainings = weekly_count
    stats.monthly_trainings = monthly_count
    stats.save()
    return stats


def update_personal_records(session: UserTrainingSession) -> list[PersonalRecord]:
    """从一次完成的训练中提取并更新个人纪录。"""
    updated: list[PersonalRecord] = []
    if not session.is_completed:
        return updated

    for record in session.exercise_records.select_related("exercise"):
        weights = _numeric(record.weights_used)
        reps = _numeric(record.reps_completed)
        sets = build_sets(record.weights_used, record.reps_completed, record.rir)
        estimate = estimate_session_e1rm(sets)
        candidates = {
            "max_weight": max(weights) if weights else 0,
            "max_reps": max(reps) if reps else 0,
            "max_volume": _record_volume(record),
            "best_form": float(record.form_score or 0),
            "e1rm": estimate.e1rm if estimate else 0,
        }
        for record_type, value in candidates.items():
            if value <= 0:
                continue
            existing = PersonalRecord.objects.filter(
                user=session.user,
                exercise=record.exercise,
                record_type=record_type,
            ).first()
            if existing and existing.value >= value:
                continue
            if existing:
                existing.value = value
                existing.achieved_at = record.created_at or timezone.now()
                existing.session = session
                existing.save(update_fields=["value", "achieved_at", "session"])
                updated.append(existing)
            else:
                updated.append(
                    PersonalRecord.objects.create(
                        user=session.user,
                        exercise=record.exercise,
                        record_type=record_type,
                        value=value,
                        achieved_at=record.created_at or timezone.now(),
                        session=session,
                    )
                )
    return updated


def evaluate_achievements(user) -> list[UserAchievement]:
    """检查并解锁所有已达成但尚未入库的成就。"""
    metrics = build_metrics(user)
    unlocked: list[UserAchievement] = []
    achievements = Achievement.objects.filter(is_active=True).order_by(
        "sort_order", "id"
    )

    for achievement in achievements:
        if UserAchievement.objects.filter(
            user=user, achievement=achievement
        ).exists():
            continue

        metric_value = float(metrics.get(achievement.metric, 0) or 0)
        if metric_value < achievement.threshold:
            continue

        user_achievement, created = UserAchievement.objects.get_or_create(
            user=user,
            achievement=achievement,
            defaults={"progress_value": metric_value},
        )
        if not created:
            continue
        unlocked.append(user_achievement)
        award_xp(
            user,
            "achievement",
            achievement.id,
            achievement.xp_reward,
            note=f"解锁成就：{achievement.title}",
        )
        # 成就奖励可能让等级达到新阈值，同步刷新等级指标。
        metrics["level"] = UserProgress.objects.get(user=user).level

    return unlocked


def record_session_completed(session: UserTrainingSession) -> dict:
    """训练完成后的统一结算入口（由信号调用）。"""
    if not session.is_completed:
        return {"xp": 0, "achievements": []}

    user = session.user
    with transaction.atomic():
        progress, _ = UserProgress.objects.select_for_update().get_or_create(
            user=user
        )
        dates = _training_dates(user)
        current_streak, longest_streak = streaks_from_dates(dates)
        progress.current_streak = current_streak
        progress.longest_streak = max(progress.longest_streak, longest_streak)
        progress.last_training_date = max(dates) if dates else None
        progress.total_sessions = _completed_sessions(user).count()
        progress.save(
            update_fields=[
                "current_streak",
                "longest_streak",
                "last_training_date",
                "total_sessions",
                "updated_at",
            ]
        )

        xp = session_xp(session, current_streak)
        _, created = award_xp(
            user,
            "session",
            session.id,
            xp,
            note=f"完成训练：{session.plan.name if session.plan else '自定义训练'}",
        )

        records = update_personal_records(session)
        refresh_user_stats(user)
        achievements = evaluate_achievements(user)

    return {
        "xp": xp if created else 0,
        "achievements": achievements,
        "records": records,
    }


# ---------------------------------------------------------------------------
# 每日任务
# ---------------------------------------------------------------------------
def daily_metrics(user, day: date | None = None) -> dict:
    day = day or timezone.localdate()
    sessions = _completed_sessions(user).filter(start_time__date=day)
    session_count = sessions.count()

    total_minutes = 0.0
    for start_time, end_time in sessions.values_list("start_time", "end_time"):
        if start_time and end_time:
            total_minutes += max(0.0, (end_time - start_time).total_seconds() / 60)

    calories = float(
        sessions.aggregate(value=Sum("calories_burned"))["value"] or 0
    )
    records = UserTrainingExerciseRecord.objects.filter(
        session__user=user,
        session__is_completed=True,
        session__start_time__date=day,
    )
    best_form = float(records.aggregate(value=Max("form_score"))["value"] or 0)
    distinct_exercises = records.values("exercise_id").distinct().count()
    volume = sum(_record_volume(record) for record in records.only(
        "weights_used", "reps_completed"
    ))

    return {
        "sessions": session_count,
        "minutes": round(total_minutes, 1),
        "calories": round(calories, 1),
        "best_form_score": best_form,
        "distinct_exercises": distinct_exercises,
        "volume": round(volume, 1),
    }


def ensure_daily_quests(user, day: date | None = None) -> list[UserDailyQuest]:
    """按用户与日期确定性挑选 3 个任务，同一天重复请求不会重复创建。"""
    day = day or timezone.localdate()
    offset = (int(user.id) + day.toordinal()) % len(QUEST_POOL)
    chosen = [QUEST_POOL[(offset + index) % len(QUEST_POOL)] for index in range(3)]

    quests: list[UserDailyQuest] = []
    for spec in chosen:
        quest, _ = UserDailyQuest.objects.get_or_create(
            user=user,
            date=day,
            code=spec["code"],
            defaults={
                "title": spec["title"],
                "description": spec["description"],
                "metric": spec["metric"],
                "target": spec["target"],
                "xp_reward": spec["xp_reward"],
            },
        )
        quests.append(quest)
    return quests


def refresh_daily_quests(user, day: date | None = None) -> list[UserDailyQuest]:
    day = day or timezone.localdate()
    quests = ensure_daily_quests(user, day)
    metrics = daily_metrics(user, day)

    now = timezone.now()
    for quest in quests:
        progress = float(metrics.get(quest.metric, 0) or 0)
        changed = False
        if progress != quest.progress:
            quest.progress = progress
            changed = True
        if progress >= quest.target and quest.completed_at is None:
            quest.completed_at = now
            changed = True
        if changed:
            quest.save(update_fields=["progress", "completed_at"])
    return quests


def claim_daily_quest(user, quest_id: int) -> tuple[UserDailyQuest, bool]:
    day = timezone.localdate()
    quest = UserDailyQuest.objects.filter(user=user, id=quest_id, date=day).first()
    if not quest:
        raise ValueError("任务不存在或已过期")
    if quest.progress < quest.target:
        raise ValueError("任务尚未完成")
    if quest.claimed_at:
        raise ValueError("奖励已经领取过了")

    quest.claimed_at = timezone.now()
    quest.save(update_fields=["claimed_at"])
    award_xp(user, "quest", quest.id, quest.xp_reward, note=f"每日任务：{quest.title}")
    return quest, True


# ---------------------------------------------------------------------------
# 每周目标
# ---------------------------------------------------------------------------
def weekly_goal_for(user, day: date | None = None) -> WeeklyGoal:
    week_start = week_start_for(day)
    goal, _ = WeeklyGoal.objects.get_or_create(
        user=user,
        week_start=week_start,
        defaults={"target_sessions": 3, "target_minutes": 150},
    )
    return goal


def weekly_goal_metrics(user, goal: WeeklyGoal) -> dict:
    week_end = goal.week_start + timedelta(days=7)
    sessions = _completed_sessions(user).filter(
        start_time__date__gte=goal.week_start,
        start_time__date__lt=week_end,
    )
    dates = set(sessions.values_list("start_time__date", flat=True))
    total_minutes = 0.0
    for start_time, end_time in sessions.values_list("start_time", "end_time"):
        if start_time and end_time:
            total_minutes += max(0.0, (end_time - start_time).total_seconds() / 60)

    completed_days = len(dates)
    completed_minutes = int(total_minutes)
    sessions_done = completed_days >= goal.target_sessions
    minutes_done = completed_minutes >= goal.target_minutes

    return {
        "completed_days": completed_days,
        "completed_minutes": completed_minutes,
        "sessions_done": sessions_done,
        "minutes_done": minutes_done,
        "can_claim": sessions_done and minutes_done and not goal.reward_claimed,
        "days_percent": round(
            min(100.0, completed_days / max(1, goal.target_sessions) * 100), 1
        ),
        "minutes_percent": round(
            min(100.0, completed_minutes / max(1, goal.target_minutes) * 100), 1
        ),
    }


def claim_weekly_goal(user) -> tuple[WeeklyGoal, int]:
    goal = weekly_goal_for(user)
    metrics = weekly_goal_metrics(user, goal)
    if goal.reward_claimed:
        raise ValueError("本周奖励已经领取过了")
    if not metrics["can_claim"]:
        raise ValueError("本周目标尚未完成")
    goal.reward_claimed = True
    goal.save(update_fields=["reward_claimed"])
    award_xp(
        user,
        "weekly_goal",
        goal.id,
        WEEKLY_GOAL_XP,
        note=f"完成每周目标（{goal.week_start}）",
    )
    return goal, WEEKLY_GOAL_XP


# ---------------------------------------------------------------------------
# 限时挑战
# ---------------------------------------------------------------------------
def challenge_window(challenge: Challenge, day: date | None = None) -> tuple[date, date]:
    """返回挑战当前周期的 [开始, 结束) 日期。"""
    day = day or timezone.localdate()
    if challenge.period == "monthly":
        start = day.replace(day=1)
        if start.month == 12:
            end = start.replace(year=start.year + 1, month=1)
        else:
            end = start.replace(month=start.month + 1)
        return start, end

    start = week_start_for(day)
    return start, start + timedelta(days=7)


def _challenge_metrics(user, start: date, end: date) -> dict:
    """统计用户在 [start, end) 内的训练指标，供所有同周期挑战复用。"""
    sessions = _completed_sessions(user).filter(
        start_time__date__gte=start,
        start_time__date__lt=end,
    )
    training_days = len(set(sessions.values_list("start_time__date", flat=True)))

    total_minutes = 0.0
    for start_time, end_time in sessions.values_list("start_time", "end_time"):
        if start_time and end_time:
            total_minutes += max(0.0, (end_time - start_time).total_seconds() / 60)

    calories = float(sessions.aggregate(value=Sum("calories_burned"))["value"] or 0)
    records = UserTrainingExerciseRecord.objects.filter(
        session__user=user,
        session__is_completed=True,
        session__start_time__date__gte=start,
        session__start_time__date__lt=end,
    )
    best_form = float(records.aggregate(value=Max("form_score"))["value"] or 0)
    distinct_exercises = records.values("exercise_id").distinct().count()
    volume = sum(
        _record_volume(record)
        for record in records.only("weights_used", "reps_completed")
    )

    return {
        "sessions": sessions.count(),
        "training_days": training_days,
        "minutes": round(total_minutes, 1),
        "calories": round(calories, 1),
        "volume": round(volume, 1),
        "distinct_exercises": distinct_exercises,
        "best_form_score": best_form,
    }


def challenge_states(user, day: date | None = None) -> list[dict]:
    """返回全部启用挑战在当前周期的进度与领取状态。"""
    challenges = list(Challenge.objects.filter(is_active=True))
    entries = {
        (entry.challenge_id, entry.period_start): entry
        for entry in UserChallenge.objects.filter(user=user)
    }
    metrics_cache: dict[tuple[date, date], dict] = {}
    states: list[dict] = []

    for challenge in challenges:
        start, end = challenge_window(challenge, day)
        key = (start, end)
        if key not in metrics_cache:
            metrics_cache[key] = _challenge_metrics(user, start, end)
        metrics = metrics_cache[key]

        progress = float(metrics.get(challenge.metric, 0) or 0)
        target = float(challenge.target or 0)
        entry = entries.get((challenge.id, start))
        is_completed = progress >= target
        claimed_at = entry.claimed_at if entry else None

        states.append(
            {
                "challenge": challenge,
                "period_start": start,
                "period_end": end - timedelta(days=1),
                "metrics": metrics,
                "progress": round(progress, 1),
                "progress_percent": (
                    100.0
                    if target <= 0
                    else round(min(100.0, progress / target * 100), 1)
                ),
                "is_joined": entry is not None,
                "is_completed": is_completed,
                "is_claimed": claimed_at is not None,
                "can_claim": entry is not None and is_completed and claimed_at is None,
                "joined_at": entry.joined_at if entry else None,
                "claimed_at": claimed_at,
            }
        )

    return states


def join_challenge(user, challenge_id: int) -> tuple[Challenge, UserChallenge, bool]:
    """参加当前周期的挑战；重复参加返回已有记录。"""
    challenge = Challenge.objects.filter(id=challenge_id, is_active=True).first()
    if not challenge:
        raise ValueError("挑战不存在或已下线")

    start, _ = challenge_window(challenge)
    entry, created = UserChallenge.objects.get_or_create(
        user=user,
        challenge=challenge,
        period_start=start,
    )
    return challenge, entry, created


def claim_challenge(
    user, challenge_id: int
) -> tuple[Challenge, UserChallenge, dict | None, list, bool]:
    """领取挑战奖励，返回 (挑战, 参与记录, 最新状态, 新解锁成就, 是否发放经验)。"""
    with transaction.atomic():
        challenge = Challenge.objects.filter(id=challenge_id, is_active=True).first()
        if not challenge:
            raise ValueError("挑战不存在或已下线")

        start, end = challenge_window(challenge)
        entry = (
            UserChallenge.objects.select_for_update()
            .filter(user=user, challenge=challenge, period_start=start)
            .first()
        )
        if not entry:
            raise ValueError("请先参加这个挑战")
        if entry.claimed_at:
            raise ValueError("奖励已经领取过了")

        metrics = _challenge_metrics(user, start, end)
        progress = float(metrics.get(challenge.metric, 0) or 0)
        if progress < float(challenge.target or 0):
            raise ValueError("挑战尚未完成")

        now = timezone.now()
        entry.completed_at = entry.completed_at or now
        entry.claimed_at = now
        entry.save(update_fields=["completed_at", "claimed_at"])
        _, awarded = award_xp(
            user,
            "challenge",
            entry.id,
            challenge.xp_reward,
            note=f"完成挑战：{challenge.title}（{start}）",
        )
        achievements = evaluate_achievements(user)

    state = next(
        (
            item
            for item in challenge_states(user)
            if item["challenge"].id == challenge.id
            and item["period_start"] == start
        ),
        None,
    )
    return challenge, entry, state, achievements, awarded


# ---------------------------------------------------------------------------
# 周榜与状态
# ---------------------------------------------------------------------------
def _display_name(user, is_me: bool) -> str:
    profile = getattr(user, "profile", None)
    nickname = (getattr(profile, "nickname", "") or "").strip()
    if is_me:
        return nickname or user.username
    if nickname:
        return nickname
    return f"{user.username[:2]}***"


def weekly_leaderboard(user, limit: int = 20) -> dict:
    week_start = week_start_for()
    start_dt = timezone.make_aware(datetime.combine(week_start, time.min))

    weekly_xp = {
        row["user"]: row["total"]
        for row in XPEvent.objects.filter(created_at__gte=start_dt)
        .values("user")
        .annotate(total=Sum("amount"))
    }

    progresses = {
        progress.user_id: progress
        for progress in UserProgress.objects.select_related("user", "user__profile")
        .filter(is_public=True)
    }
    own_progress, _ = UserProgress.objects.get_or_create(user=user)
    progresses.setdefault(user.id, own_progress)

    ranked = []
    for user_id, progress in progresses.items():
        ranked.append(
            {
                "user_id": user_id,
                "user": progress.user,
                "weekly_xp": int(weekly_xp.get(user_id, 0)),
                "total_xp": progress.xp,
                "level": progress.level,
            }
        )

    ranked.sort(key=lambda item: (-item["weekly_xp"], -item["total_xp"], item["user_id"]))

    entries = []
    me = None
    for index, item in enumerate(ranked, start=1):
        is_me = item["user_id"] == user.id
        entry = {
            "rank": index,
            "display_name": _display_name(item["user"], is_me),
            "weekly_xp": item["weekly_xp"],
            "total_xp": item["total_xp"],
            "level": item["level"],
            "level_title": level_title(item["level"]),
            "is_me": is_me,
        }
        if is_me:
            me = entry
        if index <= limit:
            entries.append(entry)

    return {
        "week_start": week_start,
        "entries": entries,
        "me": me,
        "total_participants": len(ranked),
    }


def daily_training_loads(user, days: int = HISTORY_DAYS) -> list[DailyLoad]:
    """把最近 `days` 天完成的会话聚合为引擎需要的每日负荷。

    只做取数与聚合，评分规则全部放在 `utils.readiness` 里，便于脱离 Django 单测。
    """
    today = timezone.localdate()
    since = today - timedelta(days=days - 1)

    minutes_by_day: dict[date, float] = {}
    intensity_by_day: dict[date, list[float]] = {}
    for session_day, start, end, performance in (
        _completed_sessions(user)
        .filter(start_time__date__gte=since)
        .values_list("start_time__date", "start_time", "end_time", "performance_score")
    ):
        if start and end:
            minutes = max(0.0, (end - start).total_seconds() / 60)
        else:
            minutes = 0.0
        minutes_by_day[session_day] = minutes_by_day.get(session_day, 0.0) + minutes
        intensity_by_day.setdefault(session_day, []).append(float(performance or 0.0))

    form_by_day = {
        row["session__start_time__date"]: float(row["value"] or 0.0)
        for row in (
            UserTrainingExerciseRecord.objects.filter(
                session__user=user,
                session__is_completed=True,
                session__start_time__date__gte=since,
            )
            .values("session__start_time__date")
            .annotate(value=Avg("form_score"))
        )
    }

    loads: list[DailyLoad] = []
    for session_day, minutes in minutes_by_day.items():
        scores = intensity_by_day.get(session_day) or [0.0]
        mean_performance = sum(scores) / len(scores)
        loads.append(
            DailyLoad(
                day=session_day,
                load=session_load(minutes, mean_performance),
                minutes=minutes,
                form_score=form_by_day.get(session_day),
            )
        )
    return sorted(loads, key=lambda item: item.day)


def muscle_works(user, days: int = 30) -> list[MuscleWork]:
    """把最近 `days` 天的动作记录翻译成分肌群刺激量。

    时间统一取会话开始时间（而不是 `created_at`），否则回填的历史数据会把
    恢复曲线压到最近几天。次数取 `reps_completed` 之和，计时动作用实际秒数。
    """
    since = timezone.now() - timedelta(days=days)
    rows = (
        UserTrainingExerciseRecord.objects.filter(
            session__user=user,
            session__is_completed=True,
            session__start_time__gte=since,
        )
        .select_related("exercise")
        .values_list(
            "exercise__target_muscle",
            "session__start_time",
            "sets_completed",
            "reps_completed",
            "duration_seconds_actual",
            "form_score",
        )
    )

    works: list[MuscleWork] = []
    for muscle, start, sets, reps, seconds, form_score in rows:
        if not start:
            continue
        total_reps = 0
        if isinstance(reps, (list, tuple)):
            for value in reps:
                try:
                    total_reps += max(0, int(value))
                except (TypeError, ValueError):
                    continue
        works.append(
            MuscleWork(
                muscle=muscle or "full_body",
                at=start,
                sets=int(sets or 0),
                reps=total_reps,
                seconds=float(seconds or 0.0),
                form_score=float(form_score) if form_score else None,
            )
        )
    return works


def muscle_recovery_snapshot(user, days: int = 30) -> RecoverySnapshot:
    """今日分肌群恢复快照：每个肌群的恢复度、残余疲劳、本周容量与建议。

    返回引擎对象（而不是字典），推荐链路可以直接用 `multiplier_for` 加权，
    API 层再调 `as_dict()` 序列化。
    """
    return muscle_recovery(muscle_works(user, days=days), timezone.now(), muscles=MUSCLE_ORDER)


def strength_history(user, days: int = 120) -> list[dict]:
    """每个动作的 e1RM 序列，供前端画力量曲线。

    每条点对应一次训练里该动作的估计 e1RM；估算不出来（例如自重动作没有重量）
    的训练会被跳过，避免曲线出现虚假的断点。
    """
    since = timezone.now() - timedelta(days=days)
    records = (
        UserTrainingExerciseRecord.objects.filter(
            session__user=user,
            session__is_completed=True,
            session__start_time__gte=since,
        )
        .select_related("exercise")
        .order_by("session__start_time")
    )

    grouped: dict[int, dict] = {}
    for record in records:
        sets = build_sets(record.weights_used, record.reps_completed, record.rir)
        estimate = estimate_session_e1rm(sets)
        if estimate is None or estimate.e1rm <= 0:
            continue

        entry = grouped.setdefault(
            record.exercise_id,
            {
                "exercise_id": record.exercise_id,
                "name": record.exercise.name,
                "target_muscle": record.exercise.target_muscle,
                "points": [],
            },
        )
        heaviest = max(sets, key=lambda item: item.weight) if sets else None
        entry["points"].append(
            {
                "date": timezone.localtime(record.session.start_time).date().isoformat(),
                "e1rm": round(estimate.e1rm, 1),
                "weight": round(heaviest.weight, 1) if heaviest else 0,
                "reps": heaviest.reps if heaviest else 0,
                "method": estimate.method,
            }
        )

    results: list[dict] = []
    for entry in grouped.values():
        points = entry["points"]
        e1rms = [point["e1rm"] for point in points]
        dates = [point["date"] for point in points]
        summary = strength_summary(e1rms, dates)
        entry["points"] = points
        entry["summary"] = summary
        entry["e1rm"] = summary["latest"]
        entry["best"] = summary["best"]
        entry["trend"] = summary["trend"]
        results.append(entry)

    results.sort(key=lambda item: item.get("best", 0), reverse=True)
    return results


def strength_prescription(
    user,
    exercise_id: int,
    target_reps: int = 6,
    target_rir: int = 2,
) -> dict:
    """给出某个动作下一次训练的建议重量。

    基准取该动作的历史最好 e1RM，再用双进阶规则给出下一组的重量。
    """
    history = [item for item in strength_history(user) if item["exercise_id"] == exercise_id]
    if not history:
        return {"available": False, "reason": "还没有这个动作的负重训练记录"}

    entry = history[0]
    best = float(entry.get("best") or 0)
    if best <= 0:
        return {"available": False, "reason": "还没有足够的数据估计 1RM"}

    points = entry["points"]
    last = points[-1]
    prescription = next_prescription(
        best,
        last.get("weight", 0),
        last.get("reps", 0),
        target_reps=target_reps,
        target_rir=target_rir,
    )
    return {
        "available": True,
        "exercise_id": exercise_id,
        "name": entry["name"],
        "e1rm": round(best, 1),
        "trend": entry.get("trend", 0),
        "deload": entry["summary"]["deload"],
        **prescription.as_dict(),
    }


def load_curve_for(user, days: int = 90, step: int = 1) -> list[dict]:
    """最近 `days` 天的体能 / 疲劳 / TSB 曲线，供前端画负荷走势图。

    冲激响应需要回看更长的历史，所以取数窗口比展示窗口多一个 `HISTORY_DAYS`。
    """
    loads = daily_training_loads(user, days=HISTORY_DAYS + days)
    return load_curve(loads, timezone.localdate(), days=days, step=step)


def readiness_snapshot(user) -> dict:
    """服务端就绪度评分。

    使用 `utils.readiness` 中的组合模型：Banister 体能-疲劳冲激响应（TSB）、
    EWMA 版 ACWR、Foster 单调性/紧张度，再叠加动作质量趋势与恢复间隔。
    """
    today = timezone.localdate()
    report = readiness_report(daily_training_loads(user), today)
    payload = report.as_dict()

    # 与旧接口保持兼容的几个字段
    payload["fatigue_level"] = round(min(1.0, max(0.0, report.components.acwr / 3.0)), 3)
    payload["trained_today"] = _completed_sessions(user).filter(start_time__date=today).exists()
    payload["weekly_days"] = (
        _completed_sessions(user)
        .filter(start_time__date__gte=week_start_for())
        .values("start_time__date")
        .distinct()
        .count()
    )
    return payload
