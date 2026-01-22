from django.db import models
from django.contrib.auth.models import User
from training.models import UserTrainingExerciseRecord
from exercises.models import Exercise

class AIAnalysisSession(models.Model):
    """AI 分析记录模型，记录单次动作的详细 AI 处理数据"""
    record = models.OneToOneField(
        UserTrainingExerciseRecord, 
        on_delete=models.CASCADE, 
        related_name='ai_analysis',
        verbose_name="训练记录"
    )
    video_path = models.FileField("原始视频/流路径", upload_to='ai_sessions/', null=True, blank=True)
    processed_frames = models.IntegerField("处理帧数", default=0)
    average_confidence = models.FloatField("平均置信度", default=0.0)
    
    # 关键点数据流，可以存储为大 JSON 或指向外部存储
    motion_data = models.JSONField("运动轨迹数据", null=True, blank=True)
    
    analysis_time = models.DateTimeField("分析时间", auto_now_add=True)

    class Meta:
        verbose_name = "AI 分析会话"
        verbose_name_plural = "AI 分析会话"

    def __str__(self):
        return f"AI Analysis for Record {self.record_id}"

class AIModelConfig(models.Model):
    """AI 模型配置，描述不同动作的识别参数"""
    exercise = models.ForeignKey(Exercise, on_delete=models.CASCADE, verbose_name="关联动作")
    model_version = models.CharField("模型版本", max_length=50)
    config_data = models.JSONField("配置参数", help_text="如角度阈值、关键点索引等")
    is_active = models.BooleanField("是否当前使用", default=True)
    
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "AI 模型配置"
        verbose_name_plural = "AI 模型配置"

    def __str__(self):
        return f"{self.exercise.name} - {self.model_version}"
