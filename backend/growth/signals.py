from django.db.models.signals import post_save
from django.dispatch import receiver

from training.models import UserTrainingExerciseRecord, UserTrainingSession

from .services import record_session_completed, update_personal_records


@receiver(post_save, sender=UserTrainingSession)
def handle_training_session_saved(sender, instance, **kwargs):
    """训练完成后统一结算 XP、连续天数、个人纪录与成就。"""
    if instance.is_completed:
        record_session_completed(instance)


@receiver(post_save, sender=UserTrainingExerciseRecord)
def handle_exercise_record_saved(sender, instance, **kwargs):
    """已结束会话中的动作记录变化时，同步刷新个人纪录。"""
    try:
        session = instance.session
    except UserTrainingSession.DoesNotExist:
        return
    if session.is_completed:
        update_personal_records(session)
