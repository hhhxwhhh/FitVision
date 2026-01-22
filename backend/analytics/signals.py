from django.db.models.signals import post_save, post_delete
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

@receiver([post_save, post_delete], sender=UserTrainingExerciseRecord)
def update_exercise_progress(sender, instance, **kwargs):
    """
    当动作记录发生任何变动（增、删、改）时，全量重新计算该动作的进步追踪。
    """
    # 获取关联信息（加个 try 是为了防止删除时找不到关联对象）
    try:
        date = instance.created_at.date()
        user = instance.session.user
        exercise = instance.exercise
    except AttributeError:
        # 如果是删除操作且关联对象已丢失，无法统计，直接返回
        return

    # 1. 获取或创建当天的统计行
    progress, created = ExerciseProgress.objects.get_or_create(
        user=user,
        exercise=exercise,
        date=date
    )

    # ✅ 优化点2：查出当天“所有”有效的记录（Source of Truth）
    # 不管你是改了还是删了，我只信数据库里现在还存在的记录
    all_records = UserTrainingExerciseRecord.objects.filter(
        session__user=user,
        exercise=exercise,
        created_at__date=date
    )

    # 2. 初始化变量（准备从 0 开始算）
    max_w = 0.0
    max_r = 0
    total_vol = 0.0
    best_score = 0.0

    # 3. 循环遍历每一条记录，重新累加
    for record in all_records:
        # 数据清洗：解析 JSON 里的重量和次数
        # 假设 weights_used 是 [20, 20] 这种列表
        w_list = [float(w) for w in record.weights_used if str(w).replace('.', '', 1).isdigit()]
        r_list = [int(r) for r in record.reps_completed if str(r).isdigit()]
        
        # 找最大值
        if w_list:
            current_max_w = max(w_list)
            if current_max_w > max_w: max_w = current_max_w
            
        if r_list:
            current_max_r = max(r_list)
            if current_max_r > max_r: max_r = current_max_r

        # 算容量 (Volume)
        if len(w_list) == len(r_list):
            # 这里的计算逻辑和你原来一样，但是是在循环里
            vol = sum(w * r for w, r in zip(w_list, r_list))
            total_vol += vol
        
        # 找最佳分数
        if record.form_score > best_score:
            best_score = record.form_score

    # ✅ 优化点3：直接覆盖赋值 (=)，而不是累加 (+=)
    progress.max_weight = max_w
    progress.max_reps = max_r
    progress.total_volume = total_vol 
    progress.best_form_score = best_score
    
    progress.save()
    print(f"✅ 动作 {exercise.name} 统计已更新，当前总容量: {total_vol}")