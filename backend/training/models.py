from django.db import models
from django.contrib.auth.models import User
from exercises.models import Exercise, UserExerciseRecord, ExerciseCategory

class TrainingPlan(models.Model):
    """训练计划模型"""
    DIFFICULTY_CHOICES = [
        ('beginner', '入门'),
        ('intermediate', '中级'),
        ('advanced', '高级'),
    ]

    GOAL_CHOICES = [
        ('weight_loss', '减脂'),
        ('muscle_gain', '增肌'),
        ('strength', '力量'),
        ('endurance', '耐力'),
        ('flexibility', '柔韧性'),
        ('general_fitness', '综合健身'),
    ]

    name = models.CharField("计划名称", max_length=100)
    description = models.TextField("计划描述")
    goal = models.CharField("训练目标", max_length=20, choices=GOAL_CHOICES)
    difficulty = models.CharField("难度等级", max_length=20, choices=DIFFICULTY_CHOICES, default='beginner')
    duration_weeks = models.IntegerField("计划周期(周)", default=4, help_text="训练计划总周数")

    category = models.ForeignKey(
        ExerciseCategory, 
        on_delete=models.SET_NULL, 
        null=True, 
        blank=True, 
        verbose_name="训练分类"
    )

    is_public = models.BooleanField("是否公开", default=False)
    created_by = models.ForeignKey(User, on_delete=models.CASCADE, verbose_name="创建者")

    estimated_calories_burned = models.IntegerField("预计消耗卡路里", default=0, 
                                                  help_text="整个计划预计消耗的卡路里")
    estimated_duration_minutes = models.IntegerField("预计时长(分钟)", default=0,
                                                   help_text="每次训练预计时长")
    
    is_active = models.BooleanField("是否启用", default=True)
    created_at = models.DateTimeField("创建时间", auto_now_add=True)
    updated_at = models.DateTimeField("更新时间", auto_now=True)
    
    class Meta:
        verbose_name = "训练计划"
        verbose_name_plural = "训练计划"
        ordering = ['-created_at']

    def __str__(self):
        return self.name


class TrainingPlanDay(models.Model):
    """训练计划每日安排模型"""
    plan=models.ForeignKey(TrainingPlan, on_delete=models.CASCADE, verbose_name="训练计划")
    day_number = models.IntegerField("第几天", help_text="在训练计划中的第几天")
    title = models.CharField("当日标题", max_length=100, help_text="例如：上肢力量训练")
    description = models.TextField("当日描述", blank=True)

    is_rest_day = models.BooleanField("是否休息日", default=False, help_text="如果是休息日，则不包含任何训练动作")

    warmup_duration = models.IntegerField("热身时长(分钟)", default=5)
    cooldown_duration = models.IntegerField("拉伸时长(分钟)", default=5)

    class Meta:
        verbose_name = "训练计划每日安排"
        verbose_name_plural = "训练计划每日安排"
        ordering = ['day_number']
        unique_together = ('plan', 'day_number')

    def __str__(self):
        return f"{self.plan.name} - 第{self.day_number}天"
    

class TrainingPlanExercise(models.Model):
    """训练计划动作安排模型"""

    training_day=models.ForeignKey(TrainingPlanDay, on_delete=models.CASCADE, related_name="exercises", verbose_name="训练计划每日安排")
    exercise=models.ForeignKey(Exercise,on_delete=models.CASCADE, verbose_name="动作")

    sets=models.IntegerField("组数", default=3)
    reps=models.IntegerField("每组次数", default=10)
    duration_seconds=models.IntegerField("每组时长(秒)", default=60, help_text="如果是计时动作，则填写每组持续时间")
    
    weight=models.FloatField("重量(kg)", default=0.0, help_text="如果是重量动作，则填写重量")

    rest_between_sets=models.IntegerField("组间休息时间(秒)", default=60)

    order=models.IntegerField("顺序", default=1, help_text="在当天训练中的顺序")
    notes=models.TextField("备注", blank=True)

    class Meta:
        verbose_name = "训练计划动作安排"
        verbose_name_plural = "训练计划动作安排"
        ordering = ['training_day', 'order']
        unique_together = ('training_day', 'order')
    def __str__(self):
        return f"{self.training_day.plan.name} - {self.training_day.title} - {self.exercise.name}"
    

class UserTrainingSession(models.Model):
    """用户训练会话记录模型"""
    user = models.ForeignKey(User, on_delete=models.CASCADE, verbose_name="用户")
    plan = models.ForeignKey(TrainingPlan, on_delete=models.SET_NULL, null=True, verbose_name="训练计划")
    plan_day = models.ForeignKey(TrainingPlanDay, on_delete=models.SET_NULL, null=True, verbose_name="训练日")
    
    # 会话信息
    start_time = models.DateTimeField("开始时间")
    end_time = models.DateTimeField("结束时间", null=True, blank=True)
    is_completed = models.BooleanField("是否完成", default=False)
    
    # 统计数据
    total_exercises = models.IntegerField("总动作数", default=0)
    completed_exercises = models.IntegerField("已完成动作数", default=0)
    calories_burned = models.FloatField("消耗卡路里", default=0.0)
    performance_score = models.FloatField("表现评分", default=0.0, 
                                        help_text="基于完成度和动作质量的综合评分")

    ai_analysis = models.TextField(
        "AI分析报告", 
        blank=True, 
        null=True, 
        help_text="DeepSeek生成的文本分析，包含HTML格式"
    )
    
    ai_tags = models.JSONField(
        "AI标签", 
        default=list, 
        blank=True, 
        null=True, 
        help_text="AI生成的总结性标签，如['核心稳定', '耐力好']"
    )
    
    class Meta:
        verbose_name = "用户训练会话"
        verbose_name_plural = "用户训练会话"
        ordering = ['-start_time']
    
    def __str__(self):
        status = "已完成" if self.is_completed else "进行中"
        return f"{self.user.username} - {self.plan.name if self.plan else '自定义训练'} ({status})"
    


class UserTrainingExerciseRecord(models.Model):
    """用户训练动作记录模型"""
    session = models.ForeignKey(UserTrainingSession, on_delete=models.CASCADE, 
                              related_name='exercise_records', verbose_name="训练会话")
    plan_exercise = models.ForeignKey(TrainingPlanExercise, on_delete=models.SET_NULL, 
                                    null=True, verbose_name="计划动作")
    exercise = models.ForeignKey(Exercise, on_delete=models.CASCADE, verbose_name="动作")
    
    # 实际完成情况
    sets_completed = models.IntegerField("完成组数", default=0)
    reps_completed = models.JSONField("每组完成次数", default=list, 
                                    help_text="每组实际完成的次数，如[10, 8, 12]")
    weights_used = models.JSONField("每组使用重量", default=list,
                                  help_text="每组使用的重量，如[20, 20, 20]")
    
    # 时长类动作记录
    duration_seconds_actual = models.IntegerField("实际时长(秒)", default=0)
    
    # 评分和反馈
    form_score = models.FloatField("动作评分", default=0.0, help_text="AI评估的动作质量(0-100)")
    feedback = models.JSONField("动作反馈", blank=True, null=True,
                              help_text="AI提供的详细动作分析")
    
    # 时间
    created_at = models.DateTimeField("创建时间", auto_now_add=True)
    
    class Meta:
        verbose_name = "用户训练动作记录"
        verbose_name_plural = "用户训练动作记录"
        ordering = ['created_at']
    
    def __str__(self):
        return f"{self.session} - {self.exercise.name}"

