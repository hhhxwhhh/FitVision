from django.db import models
from django.contrib.auth.models import User
from exercises.models import Exercise

class UserDailyStats(models.Model):
    """用户每日训练统计记录"""
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='daily_stats')
    date = models.DateField("统计日期")
    
    total_duration_minutes = models.IntegerField("总训练时长(分)", default=0)
    total_calories_burned = models.FloatField("总消耗卡路里", default=0.0)
    completed_sessions = models.IntegerField("完成会话数", default=0)
    completed_exercises = models.IntegerField("完成动作数", default=0)
    
    average_form_score = models.FloatField("平均动作评分", default=0.0)
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "每日统计"
        verbose_name_plural = "每日统计"
        unique_together = ('user', 'date')
        ordering = ['-date']

    def __str__(self):
        return f"{self.user.username} - {self.date}"

class UserBodyMetric(models.Model):
    """用户身体指标历史记录"""
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='body_metrics')
    date = models.DateField("记录日期")
    
    weight = models.FloatField("体重 (kg)")
    height = models.FloatField("身高 (cm)", null=True, blank=True)
    body_fat_percentage = models.FloatField("体脂率 (%)", null=True, blank=True)
    muscle_mass = models.FloatField("肌肉量 (kg)", null=True, blank=True)
    bmi = models.FloatField("BMI", null=True, blank=True)
    
    class Meta:
        verbose_name = "身体指标记录"
        verbose_name_plural = "身体指标记录"
        ordering = ['-date']

    def save(self, *args, **kwargs):
        if self.height and self.weight:
            self.bmi = self.weight / ((self.height / 100) ** 2)
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.user.username} - {self.date} ({self.weight}kg)"

class ExerciseProgress(models.Model):
    """针对特定动作的进步追踪"""
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='exercise_progress')
    exercise = models.ForeignKey(Exercise, on_delete=models.CASCADE)
    
    date = models.DateField("统计日期")
    max_weight = models.FloatField("最大重量 (kg)", default=0.0)
    max_reps = models.IntegerField("最高单组次数", default=0)
    total_volume = models.FloatField("总训练量 (kg)", default=0.0, help_text="重量 * 次数 * 组数")
    best_form_score = models.FloatField("最佳动作评分", default=0.0)

    class Meta:
        verbose_name = "动作进步追踪"
        verbose_name_plural = "动作进步追踪"
        unique_together = ('user', 'exercise', 'date')

    def __str__(self):
        return f"{self.user.username} - {self.exercise.name} - {self.date}"
