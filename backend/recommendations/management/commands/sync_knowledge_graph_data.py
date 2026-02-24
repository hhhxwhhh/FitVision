from django.core.management.base import BaseCommand
from django.db import transaction
from django.db.models import Count
from django.utils import timezone
from exercises.models import Exercise, UserExerciseRecord, ExerciseGraph
from recommendations.models import UserInteraction
from datetime import timedelta

class Command(BaseCommand):
    help = '同步推荐系统所需的所有数据：UserInteraction, ExerciseGraph'

    def handle(self, *args, **options):
        self.stdout.write("开始同步推荐系统数据...")
        
        # 1. 将 UserExerciseRecord 同步到 UserInteraction (只有 interaction_type='finish')
        self.sync_user_interactions()
        
        # 2. 从 UserInteraction/Record 计算动作序列并存入 ExerciseGraph
        self.populate_exercise_graph()
        
        # 3. 归一化 ExerciseGraph 的概率
        self.normalize_graph_probabilities()

        self.stdout.write(self.style.SUCCESS("推荐系统数据同步补全完成！"))

    def sync_user_interactions(self):
        self.stdout.write("正在从 UserExerciseRecord 同步交互数据...")
        records = UserExerciseRecord.objects.all()
        created_count = 0
        
        for record in records:
            # 检查是否已同步过（根据用户、练习和相近的时间戳）
            # 注意：此处简化处理，假设一次记录对应一个完成交互
            exists = UserInteraction.objects.filter(
                user=record.user,
                exercise=record.exercise,
                interaction_type='finish',
                timestamp__date=record.created_at.date()
            ).exists()
            
            if not exists:
                UserInteraction.objects.create(
                    user=record.user,
                    exercise=record.exercise,
                    interaction_type='finish',
                    score=min(1.0, record.accuracy_score / 100.0),
                    timestamp=record.created_at
                )
                created_count += 1
        
        self.stdout.write(f"同步了 {created_count} 条交互记录。")

    def populate_exercise_graph(self):
        self.stdout.write("正在计算动作之间的关联强度 (ExerciseGraph)...")
        from django.contrib.auth.models import User
        users = User.objects.all()
        path_count = 0
        
        for user in users:
            # 获取该用户练习按时间排序的列表
            interactions = list(UserInteraction.objects.filter(
                user=user, 
                interaction_type='finish'
            ).order_by('timestamp'))
            
            for i in range(len(interactions) - 1):
                prev_ex = interactions[i].exercise
                curr_ex = interactions[i+1].exercise
                
                if prev_ex == curr_ex: continue # 跳过重复
                
                # 如果两次练习间隔不超过 6 小时，认为它们在同一个“训练路径”上
                time_diff = interactions[i+1].timestamp - interactions[i].timestamp
                if time_diff < timedelta(hours=6):
                    eg, created = ExerciseGraph.objects.get_or_create(
                        from_exercise=prev_ex,
                        to_exercise=curr_ex
                    )
                    eg.weight += 1
                    eg.save()
                    path_count += 1
        
        self.stdout.write(self.style.SUCCESS(f"关联路径计算完成，共识别出 {path_count} 条有效转换路径。"))

    def normalize_graph_probabilities(self):
        self.stdout.write("正在归一化 ExerciseGraph 路径概率...")
        # 获取所有唯一的起始点
        from_ids = ExerciseGraph.objects.values_list('from_exercise_id', flat=True).distinct()
        
        for from_id in from_ids:
            # 获取该起始点的所有出口
            paths = ExerciseGraph.objects.filter(from_exercise_id=from_id)
            total_weight = sum(p.weight for p in paths)
            
            if total_weight > 0:
                for path in paths:
                    path.probability = path.weight / total_weight
                    path.save()
        
        self.stdout.write("概率归一化完成。")
