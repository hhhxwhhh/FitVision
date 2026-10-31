from django.db import models
from django.contrib.auth.models import User
from exercises.models import Exercise

class UserInteraction(models.Model):
    INTERACTION_TYPES = [
        ('view', '查看'),
        ('like', '喜欢'),
        ('skip', '跳过'),
        ('finish', '完成训练'),
        ('bookmark', '收藏'),
    ]

    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='interactions')
    exercise = models.ForeignKey(Exercise, on_delete=models.CASCADE)
    interaction_type = models.CharField(max_length=20, choices=INTERACTION_TYPES)
    score = models.FloatField(default=0.0, help_text="归一化后的交互评分")
    timestamp = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-timestamp']

class RecommendedExercise(models.Model):
    # 移除固定的 choices 以支持场景化的动态标识 (例如 discovery:cosine)
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='recommendations')
    exercise = models.ForeignKey(Exercise, on_delete=models.CASCADE)
    algorithm = models.CharField(max_length=50, help_text="使用的推荐算法或场景标识")
    score = models.FloatField(default=0.0)
    rank = models.IntegerField(default=1)
    reason = models.CharField(max_length=255, blank=True, help_text="推荐理由")
    is_seen = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['rank', '-created_at']

class UserState(models.Model):
    """用于强化学习和上下文推荐的用户实时状态"""
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='rec_state')
    fatigue_level = models.FloatField(default=0.0, help_text="疲劳度 0-1")
    target_intensity = models.FloatField(default=5.0, help_text="目标强度 1-10")
    consistency_score = models.FloatField(default=0.0, help_text="坚持程度评分")
    last_trained_at = models.DateTimeField(null=True, blank=True)
    current_equipment_available = models.CharField(max_length=100, default='all')
