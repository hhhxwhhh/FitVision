from datetime import datetime, time

from django.db.models.signals import post_save
from django.dispatch import receiver
from django.utils import timezone

from analytics.models import UserDailyStats
from .models import UserState

@receiver(post_save, sender=UserDailyStats)
def update_user_state(sender, instance, **kwargs):
    """当用户有新的统计数据产生时，更新其推荐状态"""
    state, _ = UserState.objects.get_or_create(user=instance.user)

    # 疲劳度统一交给负荷模型推导（ACWR / 3），不再用"评分低就 +0.2"的示例逻辑。
    # 模型没有可用训练历史时 resolve_fatigue_level 会回退到当前值，所以这里是幂等的。
    try:
        from .services import resolve_fatigue_level

        state.fatigue_level = resolve_fatigue_level(
            instance.user, fallback=float(state.fatigue_level or 0.0)
        )
    except Exception:  # pragma: no cover - 状态同步失败不应阻断统计写入
        pass

    state.last_trained_at = timezone.make_aware(
        datetime.combine(instance.date, time.min)
    )
    state.save()
