from django.conf import settings
from django.db import models


class UserProgress(models.Model):
    """用户在成长体系中的总进度。

    XP 与等级是激励系统的唯一事实来源；连续天数、总训练次数会在每次
    完成训练后根据训练会话重新计算，避免与统计模块出现两份互相打架的数据。
    """

    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="growth_progress",
        verbose_name="用户",
    )
    xp = models.PositiveIntegerField("累计经验", default=0)
    level = models.PositiveIntegerField("当前等级", default=1)
    current_streak = models.PositiveIntegerField("当前连续训练天数", default=0)
    longest_streak = models.PositiveIntegerField("最长连续训练天数", default=0)
    last_training_date = models.DateField("最近训练日期", null=True, blank=True)
    total_sessions = models.PositiveIntegerField("累计训练次数", default=0)
    is_public = models.BooleanField("参与周榜公开排名", default=True)
    updated_at = models.DateTimeField("更新时间", auto_now=True)

    class Meta:
        verbose_name = "成长进度"
        verbose_name_plural = "成长进度"

    def __str__(self):
        return f"{self.user.username} - Lv.{self.level} ({self.xp} XP)"


class Achievement(models.Model):
    """成就定义，由数据迁移写入，管理员也可在后台调整！"""

    CATEGORY_CHOICES = [
        ("milestone", "里程碑"),
        ("streak", "连续性"),
        ("volume", "训练量"),
        ("quality", "动作质量"),
        ("exploration", "探索"),
        ("special", "特别"),
    ]

    METRIC_CHOICES = [
        ("sessions", "完成训练次数"),
        ("streak", "当前连续天数"),
        ("longest_streak", "最长连续天数"),
        ("training_days", "累计训练天数"),
        ("minutes", "累计训练分钟"),
        ("calories", "累计消耗热量"),
        ("best_form_score", "最佳动作评分"),
        ("personal_records", "个人纪录数量"),
        ("total_volume", "累计训练容量"),
        ("distinct_exercises", "累计动作种类"),
        ("weekly_days", "本周训练天数"),
        ("early_sessions", "清晨训练次数"),
        ("night_sessions", "深夜训练次数"),
        ("challenges_claimed", "完成挑战次数"),
        ("level", "当前等级"),
    ]

    code = models.CharField("唯一标识", max_length=64, unique=True)
    title = models.CharField("成就名称", max_length=64)
    description = models.CharField("成就描述", max_length=200)
    category = models.CharField(
        "分类", max_length=20, choices=CATEGORY_CHOICES, default="milestone"
    )
    metric = models.CharField("判定指标", max_length=32, choices=METRIC_CHOICES)
    threshold = models.FloatField("达成阈值")
    xp_reward = models.PositiveIntegerField("经验奖励", default=50)
    icon = models.CharField("图标标识", max_length=32, blank=True)
    sort_order = models.IntegerField("排序", default=0)
    is_active = models.BooleanField("是否启用", default=True)

    class Meta:
        verbose_name = "成就"
        verbose_name_plural = "成就"
        ordering = ["sort_order", "id"]

    def __str__(self):
        return self.title


class UserAchievement(models.Model):
    """用户已解锁的成就。"""

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="unlocked_achievements",
        verbose_name="用户",
    )
    achievement = models.ForeignKey(
        Achievement, on_delete=models.CASCADE, verbose_name="成就"
    )
    progress_value = models.FloatField("解锁时指标值", default=0)
    unlocked_at = models.DateTimeField("解锁时间", auto_now_add=True)

    class Meta:
        verbose_name = "用户成就"
        verbose_name_plural = "用户成就"
        unique_together = ("user", "achievement")
        ordering = ["-unlocked_at"]

    def __str__(self):
        return f"{self.user.username} - {self.achievement.title}"


class UserDailyQuest(models.Model):
    """每日任务。任务按用户与日期确定性生成，进度由训练数据实时计算。"""

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="daily_quests",
        verbose_name="用户",
    )
    date = models.DateField("任务日期")
    code = models.CharField("任务标识", max_length=64)
    title = models.CharField("任务名称", max_length=64)
    description = models.CharField("任务描述", max_length=200)
    metric = models.CharField("判定指标", max_length=32)
    target = models.FloatField("目标值")
    progress = models.FloatField("当前进度", default=0)
    xp_reward = models.PositiveIntegerField("经验奖励", default=30)
    completed_at = models.DateTimeField("完成时间", null=True, blank=True)
    claimed_at = models.DateTimeField("领取时间", null=True, blank=True)
    created_at = models.DateTimeField("创建时间", auto_now_add=True)

    class Meta:
        verbose_name = "每日任务"
        verbose_name_plural = "每日任务"
        unique_together = ("user", "date", "code")
        ordering = ["date", "id"]

    def __str__(self):
        return f"{self.user.username} - {self.date} - {self.title}"

    @property
    def is_completed(self):
        return self.progress >= self.target

    @property
    def is_claimed(self):
        return self.claimed_at is not None


class WeeklyGoal(models.Model):
    """用户每周训练目标，默认 3 天 / 150 分钟。"""

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="weekly_goals",
        verbose_name="用户",
    )
    week_start = models.DateField("本周开始日期")
    target_sessions = models.PositiveIntegerField("目标训练天数", default=3)
    target_minutes = models.PositiveIntegerField("目标训练分钟", default=150)
    reward_claimed = models.BooleanField("奖励是否已领取", default=False)
    created_at = models.DateTimeField("创建时间", auto_now_add=True)
    updated_at = models.DateTimeField("更新时间", auto_now=True)

    class Meta:
        verbose_name = "每周目标"
        verbose_name_plural = "每周目标"
        unique_together = ("user", "week_start")
        ordering = ["-week_start"]

    def __str__(self):
        return f"{self.user.username} - {self.week_start}"


class PersonalRecord(models.Model):
    """用户在某个动作上的历史最佳纪录。"""

    RECORD_TYPE_CHOICES = [
        ("max_weight", "最大重量"),
        ("max_reps", "最高单组次数"),
        ("max_volume", "单次训练容量"),
        ("best_form", "最佳动作评分"),
        ("e1rm", "等效 1RM"),
    ]

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="personal_records",
        verbose_name="用户",
    )
    exercise = models.ForeignKey(
        "exercises.Exercise", on_delete=models.CASCADE, verbose_name="动作"
    )
    record_type = models.CharField(
        "纪录类型", max_length=20, choices=RECORD_TYPE_CHOICES
    )
    value = models.FloatField("纪录值")
    achieved_at = models.DateTimeField("达成时间")
    session = models.ForeignKey(
        "training.UserTrainingSession",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        verbose_name="训练会话",
    )

    class Meta:
        verbose_name = "个人纪录"
        verbose_name_plural = "个人纪录"
        unique_together = ("user", "exercise", "record_type")
        ordering = ["-achieved_at"]

    def __str__(self):
        return f"{self.user.username} - {self.exercise.name} - {self.get_record_type_display()}"


class Challenge(models.Model):
    """限时挑战定义。

    挑战按周或按月循环，进度直接从周期内的训练数据计算，不保存易漂移的缓存值。
    用户必须先参加挑战，完成目标后才能领取经验。
    """

    PERIOD_CHOICES = [
        ("weekly", "每周"),
        ("monthly", "每月"),
    ]

    METRIC_CHOICES = [
        ("sessions", "完成训练次数"),
        ("training_days", "训练天数"),
        ("minutes", "训练分钟"),
        ("calories", "消耗热量"),
        ("volume", "训练容量"),
        ("distinct_exercises", "动作种类"),
        ("best_form_score", "最佳动作评分"),
    ]

    code = models.CharField("唯一标识", max_length=64, unique=True)
    title = models.CharField("挑战名称", max_length=64)
    description = models.CharField("挑战描述", max_length=200)
    period = models.CharField(
        "周期", max_length=16, choices=PERIOD_CHOICES, default="weekly"
    )
    metric = models.CharField("判定指标", max_length=32, choices=METRIC_CHOICES)
    target = models.FloatField("目标值")
    xp_reward = models.PositiveIntegerField("经验奖励", default=60)
    icon = models.CharField("图标标识", max_length=32, blank=True)
    sort_order = models.IntegerField("排序", default=0)
    is_active = models.BooleanField("是否启用", default=True)

    class Meta:
        verbose_name = "限时挑战"
        verbose_name_plural = "限时挑战"
        ordering = ["sort_order", "id"]

    def __str__(self):
        return f"{self.title}（{self.get_period_display()}）"


class UserChallenge(models.Model):
    """用户参加某个周期挑战的记录，按周期隔离。"""

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="challenge_entries",
        verbose_name="用户",
    )
    challenge = models.ForeignKey(
        Challenge, on_delete=models.CASCADE, related_name="entries", verbose_name="挑战"
    )
    period_start = models.DateField("周期开始日期")
    joined_at = models.DateTimeField("参加时间", auto_now_add=True)
    completed_at = models.DateTimeField("完成时间", null=True, blank=True)
    claimed_at = models.DateTimeField("领取时间", null=True, blank=True)

    class Meta:
        verbose_name = "用户挑战"
        verbose_name_plural = "用户挑战"
        unique_together = ("user", "challenge", "period_start")
        ordering = ["-period_start", "id"]
        indexes = [models.Index(fields=["user", "period_start"])]

    def __str__(self):
        return f"{self.user.username} - {self.challenge.title} ({self.period_start})"

    @property
    def is_claimed(self):
        return self.claimed_at is not None


class XPEvent(models.Model):
    """经验流水，用唯一约束保证同一来源只结算一次。"""

    SOURCE_CHOICES = [
        ("session", "完成训练"),
        ("quest", "每日任务"),
        ("achievement", "解锁成就"),
        ("weekly_goal", "每周目标"),
        ("challenge", "限时挑战"),
    ]

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="xp_events",
        verbose_name="用户",
    )
    source = models.CharField("来源", max_length=20, choices=SOURCE_CHOICES)
    reference_id = models.PositiveIntegerField("来源对象 ID")
    amount = models.PositiveIntegerField("经验值")
    note = models.CharField("说明", max_length=200, blank=True)
    created_at = models.DateTimeField("创建时间", auto_now_add=True)

    class Meta:
        verbose_name = "经验流水"
        verbose_name_plural = "经验流水"
        unique_together = ("user", "source", "reference_id")
        ordering = ["-created_at"]
        indexes = [models.Index(fields=["user", "created_at"])]

    def __str__(self):
        return f"{self.user.username} +{self.amount} XP ({self.get_source_display()})"
