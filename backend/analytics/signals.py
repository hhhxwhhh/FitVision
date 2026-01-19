from django.db.models.signals import post_save
from django.dispatch import receiver
from django.db import models
from django.utils import timezone
from training.models import UserTrainingSession, UserTrainingExerciseRecord
from .models import UserDailyStats, ExerciseProgress

@receiver(post_save, sender=UserTrainingSession)
def update_daily_stats(sender, instance, **kwargs):
    """当训练会话更新且标记为完成时，更新每日统计"""
    if instance.is_completed and instance.end_time:
        today = instance.start_time.date()
        stats, created = UserDailyStats.objects.get_or_create(
            user=instance.user,
            date=today
        )
        
        # 计算当天所有完成会话的数据
        sessions = UserTrainingSession.objects.filter(
            user=instance.user, 
            start_time__date=today,
            is_completed=True
        )
        
        stats.completed_sessions = sessions.count()
        stats.total_calories_burned = sessions.aggregate(models.Sum('calories_burned'))['calories_burned__sum'] or 0
        stats.average_form_score = sessions.aggregate(models.Avg('performance_score'))['performance_score__avg'] or 0
        
        # 计算总时长
        total_minutes = 0
        for s in sessions:
            if s.end_time:
                total_minutes += (s.end_time - s.start_time).total_seconds() / 60
        
        stats.total_duration_minutes = int(total_minutes)
        stats.save()

@receiver(post_save, sender=UserTrainingExerciseRecord)
def update_exercise_progress(sender, instance, **kwargs):
    """当动作记录保存时，更新该动作的进步追踪"""
    date = instance.created_at.date()
    user = instance.session.user
    exercise = instance.exercise
    
    progress, created = ExerciseProgress.objects.get_or_create(
        user=user,
        exercise=exercise,
        date=date
    )
    
    # 获取最高重量和最高次数
    weights = [float(w) for w in instance.weights_used if str(w).replace('.', '', 1).isdigit()]
    reps = [int(r) for r in instance.reps_completed if str(r).isdigit()]
    
    if weights:
        progress.max_weight = max(progress.max_weight, max(weights))
    if reps:
        progress.max_reps = max(progress.max_reps, max(reps))
    
    # 动作平均量
    volume = sum(w * r for w, r in zip(weights, reps)) if len(weights) == len(reps) else 0
    progress.total_volume += volume
    
    progress.best_form_score = max(progress.best_form_score, instance.form_score)
    progress.save()
