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
from django.db.models import Max, Sum
from django.utils import timezone

from training.models import UserTrainingExerciseRecord, UserTrainingSession
from users.models import UserStats

from .models import (
    Achievement,
    PersonalRecord,
    UserAchievement,
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
        candidates = {
            "max_weight": max(weights) if weights else 0,
            "max_reps": max(reps) if reps else 0,
            "max_volume": _record_volume(record),
            "best_form": float(record.form_score or 0),
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


def readiness_snapshot(user) -> dict:
    """服务端就绪度评分，与首页展示保持同一套规则。"""
    from recommendations.models import UserState

    state, _ = UserState.objects.get_or_create(user=user)
    fatigue = max(0.0, min(1.0, float(state.fatigue_level or 0)))
    progress, _ = UserProgress.objects.get_or_create(user=user)
    trained_today = _completed_sessions(user).filter(
        start_time__date=timezone.localdate()
    ).exists()

    monday = week_start_for()
    weekly_days = (
        _completed_sessions(user)
        .filter(start_time__date__gte=monday)
        .values("start_time__date")
        .distinct()
        .count()
    )

    score = 94 - fatigue * 55
    if trained_today:
        score -= 4
    if progress.current_streak >= 3:
        score += 3
    if weekly_days >= 3:
        score += 2
    score = int(round(max(25.0, min(99.0, score))))

    if score >= 80:
        tone, label = "excellent", "状态极佳"
        advice = "身体信号良好，可以安排一次高质量力量或技术训练。"
    elif score >= 62:
        tone, label = "good", "适合训练"
        advice = "状态稳定，按计划完成中等强度训练即可。"
    elif score >= 45:
        tone, label = "moderate", "中等强度"
        advice = "今天适合控制强度，把注意力放在动作质量上。"
    else:
        tone, label = "recover", "恢复优先"
        advice = "疲劳度偏高，建议安排低强度恢复训练并优先保证睡眠。"

    return {
        "score": score,
        "tone": tone,
        "label": label,
        "advice": advice,
        "fatigue_level": round(fatigue, 3),
        "trained_today": trained_today,
        "weekly_days": weekly_days,
    }
