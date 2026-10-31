import json
import os
import tempfile
from pathlib import Path

from django.conf import settings
from django.contrib.auth.models import User
from django.core.management import call_command
from django.core.management.base import BaseCommand
from django.db import transaction

from exercises.models import Exercise
from training.models import TrainingPlan


class Command(BaseCommand):
    help = "在数据库为空时自动导入动作库与示例训练计划，可重复执行。"

    def add_arguments(self, parser):
        parser.add_argument(
            "--force",
            action="store_true",
            help="即使数据库中已有数据也重新导入 fixtures",
        )
        parser.add_argument(
            "--with-history",
            action="store_true",
            help="同时为演示用户生成可复现的训练历史数据",
        )

    def handle(self, *args, **options):
        force = options["force"]
        loaded = False

        if force or not Exercise.objects.exists():
            self._load_exercises()
            loaded = True
        else:
            self.stdout.write(f"动作库已存在 {Exercise.objects.count()} 个动作，跳过导入。")

        if force or not TrainingPlan.objects.exists():
            self._load_training_plan()
            loaded = True
        else:
            self.stdout.write(f"训练计划已存在 {TrainingPlan.objects.count()} 个计划，跳过导入。")

        if loaded:
            self.stdout.write(self.style.SUCCESS("演示数据已导入完成。"))
        else:
            self.stdout.write(self.style.SUCCESS("演示数据已就绪，无需导入。"))

        if options["with_history"]:
            call_command("seed_demo_history", create_user=True, force=force)

    def _fixture_path(self, relative: str) -> Path:
        return Path(settings.BASE_DIR) / relative

    def _load_exercises(self):
        fixture = self._fixture_path("exercises/fixtures/data.json")
        if not fixture.exists():
            self.stderr.write(f"未找到动作 fixture：{fixture}")
            return
        with transaction.atomic():
            call_command("loaddata", str(fixture), verbosity=0)
        self.stdout.write(
            self.style.SUCCESS(f"动作库：已导入 {Exercise.objects.count()} 个动作。")
        )

    def _load_training_plan(self):
        fixture = self._fixture_path("training/fixtures/seed.json")
        if not fixture.exists():
            self.stderr.write(f"未找到训练计划 fixture：{fixture}")
            return

        owner = self._plan_owner()
        with fixture.open(encoding="utf-8") as source:
            records = json.load(source)

        # seed.json 里写死了 created_by=1；这里改绑到实际存在的用户，
        # 避免全新数据库（还没有用户）导入时触发外键失败。
        for record in records:
            if record["model"] == "training.trainingplan":
                record["fields"]["created_by"] = owner.pk

        temporary_path = None
        try:
            with tempfile.NamedTemporaryFile(
                "w", suffix=".json", encoding="utf-8", delete=False
            ) as temporary:
                json.dump(records, temporary, ensure_ascii=False)
                temporary_path = temporary.name
            with transaction.atomic():
                call_command("loaddata", temporary_path, verbosity=0)
        finally:
            if temporary_path:
                os.unlink(temporary_path)

        self.stdout.write(
            self.style.SUCCESS(f"训练计划：已导入 {TrainingPlan.objects.count()} 个示例计划。")
        )

    @staticmethod
    def _plan_owner() -> User:
        owner = (
            User.objects.filter(is_superuser=True).order_by("id").first()
            or User.objects.order_by("id").first()
        )
        if owner:
            return owner
        owner = User.objects.create_user(
            username="fitvision_seed",
            email="seed@fitvision.local",
            password=None,
            is_active=False,
        )
        return owner
