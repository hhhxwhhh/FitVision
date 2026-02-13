from django.db.models.signals import post_save
from django.dispatch import receiver
from training.models import UserTrainingSession  # 假设有这个或者 TrainingLog
from analytics.models import UserDailyStats
from .models import UserState

@receiver(post_save, sender=UserDailyStats)
def update_user_state(sender, instance, **kwargs):
    """当用户有新的统计数据产生时，更新其推荐状态"""
    state, _ = UserState.objects.get_or_create(user=instance.user)
    
    # 根据今日评分调整疲劳度 (示例逻辑)
    if instance.average_form_score < 60:
        state.fatigue_level = min(1.0, state.fatigue_level + 0.2)
    else:
        state.fatigue_level = max(0.0, state.fatigue_level - 0.1)
        
    state.last_trained_at = instance.date
    state.save()
