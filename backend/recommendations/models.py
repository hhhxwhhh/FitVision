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
    ALGO_CHOICES = [
        ('cosine', '余弦相似度 (基于内容)'),
        ('cf', '协同过滤 (基于用户)'),
        ('ml_regression', '机器学习回归预测'),
        ('dl_sequence', '深度学习序列推荐'),
        ('rl_adaptive', '强化学习动态调整'),
        ('gnn_reasoning', '图神经网络 (知识图谱分析)'),
        ('popularity', '热门推荐 (冷启动)'),
    ]

    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='recommendations')
    exercise = models.ForeignKey(Exercise, on_delete=models.CASCADE)
    algorithm = models.CharField(max_length=20, choices=ALGO_CHOICES)
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
