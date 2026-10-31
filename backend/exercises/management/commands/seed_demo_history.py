"""Generate reproducible synthetic training history for a demo user.

The pure generator lives in ``utils/demo_data.py``; this command maps its specs
onto the ORM (sessions, per-exercise records, interactions and aggregate stats).

Note: ``UserExerciseRecord.created_at`` and ``UserInteraction.timestamp`` use
``auto_now_add``, so their timestamps cannot be set on ``create()``. We backdate
them explicitly with ``queryset.update()`` after insertion.
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
from utils.demo_data import generate_training_history, summarize_history


class Command(BaseCommand):
    help = "为演示用户生成可复现的历史训练数据（会话、动作记录、交互与统计）。"

    def add_arguments(self, parser):
        parser.add_argument("--user", default="demo", help="目标用户名（默认 demo）")
        parser.add_argument("--weeks", type=int, default=8, help="追溯多少周")
        parser.add_argument("--days-per-week", type=int, default=4, help="每周训练天数")
        parser.add_argument("--seed", type=int, default=42, help="随机种子（保证可复现）")
        parser.add_argument("--force", action="store_true", help="清空该用户已有历史后重建")
        parser.add_argument(
            "--create-user",
            action="store_true",
            help="用户不存在时自动创建（演示密码 fitvision123）",
        )
        parser.add_argument(
            "--no-periodization",
            action="store_true",
            help="关闭周期化（默认 4 周一循环：3 周渐进超负荷 + 1 周减量）",
        )

    def handle(self, *args, **options):
        username = options["user"]
        user = User.objects.filter(username=username).first()

        if user is None:
            if not options["create_user"]:
                self.stderr.write(f"用户 {username} 不存在。")
                self.stdout.write("使用 --create-user 自动创建该演示用户。")
                return
            user = User.objects.create_user(
                username=username,
                email=f"{username}@fitvision.local",
                password="fitvision123",
            )
            self._seed_profile(user)
            self.stdout.write(
                self.style.SUCCESS(f"已创建演示用户 {username}（密码 fitvision123）。")
            )

        exercises = list(Exercise.objects.filter(is_active=True))
        if not exercises:
            self.stderr.write("动作库为空，请先运行 `python manage.py seed_demo`。")
            return

        if options["force"]:
            self._clear_history(user)

        existing = UserTrainingSession.objects.filter(user=user).count()
        if existing and not options["force"]:
            self.stdout.write(
                f"用户 {username} 已有 {existing} 条训练会话，跳过。使用 --force 重建。"
            )
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

        sessions = generate_training_history(
            catalog,
            seed=options["seed"],
            weeks=options["weeks"],
            days_per_week=options["days_per_week"],
            end_date=timezone.localdate(),
            periodization=not options["no_periodization"],
        )
        if not sessions:
            self.stderr.write("未生成任何会话，请检查动作库或参数。")
            return

        created_sessions = 0
        created_records = 0

        with transaction.atomic():
            for spec in sessions:
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
                    ai_tags=[spec["focus"], "演示数据"],
                )

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
                    # created_at is auto_now_add; backdate it explicitly.
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

                created_sessions += 1

        summary = summarize_history(sessions, today=timezone.localdate())
        best_form = max(
            (entry["form_score"] for spec in sessions for entry in spec["exercises"]),
            default=0.0,
        )
        self._update_stats(user, summary, best_form)

        self.stdout.write(
            self.style.SUCCESS(
                f"已为 {username} 生成 {created_sessions} 次训练、{created_records} 条动作记录。"
            )
        )
        self.stdout.write(
            f"训练天数 {summary['training_days']} · 总时长 {summary['total_minutes']} 分钟 · "
            f"平均动作评分 {summary['average_form']} · 最长连续 {summary['longest_streak']} 天"
        )

    @staticmethod
    def _clear_history(user):
        UserTrainingSession.objects.filter(user=user).delete()
        UserExerciseRecord.objects.filter(user=user).delete()
        UserInteraction.objects.filter(user=user).delete()

    @staticmethod
    def _update_stats(user, summary, best_form):
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

    @staticmethod
    def _seed_profile(user):
        profile = getattr(user, "profile", None)
        if profile is not None:
            profile.nickname = "演示健身者"
            profile.gender = "male"
            profile.age = 26
            profile.height = 175.0
            profile.weight = 72.0
            profile.target_weight = 68.0
            profile.fitness_level = "intermediate"
            profile.activity_level = "moderate"
            profile.injury_history = "无"
            profile.save()

        # An active goal gives the recommender and AI planner real context.
        today = timezone.localdate()
        UserGoal.objects.get_or_create(
            user=user,
            goal_type="weight_loss",
            defaults={
                "target_value": 68.0,
                "current_value": 72.0,
                "start_date": today,
                "target_date": today + timedelta(days=90),
                "is_active": True,
                "achieved": False,
            },
        )
