"""Seed a balanced multi-user dataset for the recommendation pipeline.

The personas and sessions come from ``utils.demo_data.generate_population`` —
pure Python, deterministic for a given seed — and are mapped here onto the ORM.
This gives the hybrid recommender enough signal to train and evaluate on
instead of the single demo user.

As in ``seed_demo_history``, ``created_at`` / ``timestamp`` are ``auto_now_add``
fields, so historical values are written back with ``queryset.update()``.
"""

from datetime import timedelta

from django.contrib.auth.models import User
from django.core.management.base import BaseCommand
from django.db import transaction
from django.utils import timezone

from exercises.models import Exercise, UserExerciseRecord
from recommendations.models import UserInteraction
from training.models import UserTrainingExerciseRecord, UserTrainingSession
from users.models import UserGoal, UserStats
from utils.demo_data import generate_population, summarize_population

DEFAULT_PASSWORD = "fitvision123"

GOAL_TO_TYPE = {
    "weight_loss": "weight_loss",
    "muscle_gain": "muscle_gain",
    "endurance": "endurance",
    "flexibility": "flexibility",
}


class Command(BaseCommand):
    help = "生成多用户合成数据集（含档案、目标、训练历史与交互），供推荐算法训练与评测。"

    def add_arguments(self, parser):
        parser.add_argument("--users", type=int, default=12, help="生成多少个用户（默认 12）")
        parser.add_argument("--weeks", type=int, default=6, help="每人追溯多少周")
        parser.add_argument("--seed", type=int, default=7, help="随机种子（保证可复现）")
        parser.add_argument("--prefix", default="trainee", help="用户名前缀（默认 trainee）")
        parser.add_argument("--force", action="store_true", help="清空这些用户已有历史后重建")

    def handle(self, *args, **options):
        exercises = list(Exercise.objects.filter(is_active=True))
        if not exercises:
            self.stderr.write("动作库为空，请先运行 `python manage.py seed_demo`。")
            return

        catalog = [
            {
                "name": exercise.name,
                "target_muscle": exercise.target_muscle,
                "equipment": exercise.equipment,
                "calories_burned": exercise.calories_burned,
                "default_reps": exercise.default_reps,
            }
            for exercise in exercises
        ]
        by_name = {exercise.name: exercise for exercise in exercises}

        end_date = timezone.localdate()
        population = generate_population(
            catalog,
            users=options["users"],
            seed=options["seed"],
            weeks=options["weeks"],
            end_date=end_date,
        )
        if not population:
            self.stderr.write("未生成任何数据，请检查动作库或参数。")
            return

        created_sessions = 0
        created_records = 0

        with transaction.atomic():
            for persona in population:
                username = f"{options['prefix']}{persona['username'].removeprefix('trainee')}"
                user = self._get_or_create_user(username, persona)
                if options["force"]:
                    self._clear_history(user)

                for spec in persona["sessions"]:
                    session = UserTrainingSession.objects.create(
                        user=user,
                        plan=None,
                        plan_day=None,
                        start_time=spec["start_time"],
                        end_time=spec["end_time"],
                        is_completed=spec["completed"],
                        total_exercises=len(spec["exercises"]),
                        completed_exercises=(
                            len(spec["exercises"])
                            if spec["completed"]
                            else max(1, len(spec["exercises"]) - 1)
                        ),
                        calories_burned=spec["calories_burned"],
                        performance_score=spec["performance_score"],
                        ai_tags=[spec["focus"], persona["goal"], "合成数据集"],
                    )
                    created_sessions += 1

                    for entry in spec["exercises"]:
                        exercise = by_name.get(entry["name"])
                        if exercise is None:
                            continue

                        UserTrainingExerciseRecord.objects.create(
                            session=session,
                            plan_exercise=None,
                            exercise=exercise,
                            sets_completed=entry["sets"],
                            reps_completed=entry["reps"],
                            weights_used=[entry["weight"]] * entry["sets"],
                            duration_seconds_actual=entry["duration_seconds"],
                            form_score=entry["form_score"],
                        )

                        record = UserExerciseRecord.objects.create(
                            user=user,
                            exercise=exercise,
                            count=sum(entry["reps"]),
                            duration=entry["duration_seconds"],
                            accuracy_score=entry["form_score"],
                            calories_burned=entry["calories_burned"],
                        )
                        UserExerciseRecord.objects.filter(pk=record.pk).update(
                            created_at=spec["start_time"]
                        )

                        interaction = UserInteraction.objects.create(
                            user=user,
                            exercise=exercise,
                            interaction_type="finish",
                            score=min(1.0, max(0.0, entry["form_score"] / 100.0)),
                        )
                        UserInteraction.objects.filter(pk=interaction.pk).update(
                            timestamp=spec["start_time"]
                        )
                        created_records += 1

                self._update_stats(user, persona)

        summary = summarize_population(population)
        self.stdout.write(
            self.style.SUCCESS(
                f"已生成 {summary['users']} 位用户、{created_sessions} 次训练、"
                f"{created_records} 条动作记录。"
            )
        )
        self.stdout.write(
            f"水平分布 {summary['levels']} · 目标分布 {summary['goals']} · "
            f"总时长 {summary['minutes']} 分钟 · 平均动作评分 {summary['average_form']}"
        )
        self.stdout.write(f"登录密码统一为 {DEFAULT_PASSWORD}（仅用于本地演示数据）。")

    @staticmethod
    def _get_or_create_user(username, persona):
        user = User.objects.filter(username=username).first()
        if user is not None:
            return user

        user = User.objects.create_user(
            username=username,
            email=f"{username}@fitvision.local",
            password=DEFAULT_PASSWORD,
        )

        profile = getattr(user, "profile", None)
        if profile is not None:
            profile.nickname = f"{persona['level']}-{persona['goal']}"
            profile.gender = "male" if int(username[-1]) % 2 == 1 else "female"
            profile.age = 24 + int(username[-1])
            profile.height = 168.0 + int(username[-1])
            profile.weight = 62.0 + int(username[-1])
            profile.fitness_level = persona["level"]
            profile.activity_level = "moderate"
            profile.injury_history = "无"
            profile.save()

        goal_type = GOAL_TO_TYPE.get(persona["goal"], "weight_loss")
        today = timezone.localdate()
        UserGoal.objects.get_or_create(
            user=user,
            goal_type=goal_type,
            defaults={
                "target_value": 60.0,
                "current_value": 65.0,
                "start_date": today,
                "target_date": today + timedelta(days=90),
                "is_active": True,
                "achieved": False,
            },
        )
        return user

    @staticmethod
    def _clear_history(user):
        UserTrainingSession.objects.filter(user=user).delete()
        UserExerciseRecord.objects.filter(user=user).delete()
        UserInteraction.objects.filter(user=user).delete()

    @staticmethod
    def _update_stats(user, persona):
        summary = persona["summary"]
        best_form = max(
            (
                entry["form_score"]
                for spec in persona["sessions"]
                for entry in spec["exercises"]
            ),
            default=0.0,
        )
        UserStats.objects.update_or_create(
            user=user,
            defaults={
                "total_trainings": summary["sessions"],
                "total_training_days": summary["training_days"],
                "total_training_time": summary["total_minutes"],
                "total_calories_burned": summary["total_calories"],
                "best_accuracy_score": best_form,
                "longest_training_streak": summary["longest_streak"],
                "weekly_trainings": summary["weekly_sessions"],
                "monthly_trainings": summary["monthly_sessions"],
            },
        )
