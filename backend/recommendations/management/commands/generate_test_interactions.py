import os
import random
from django.core.management.base import BaseCommand
from django.contrib.auth.models import User
from exercises.models import Exercise, UserExerciseRecord
from recommendations.models import UserInteraction
from django.utils import timezone
from datetime import timedelta

class Command(BaseCommand):
    help = '生成用于测试知识图谱推荐的模拟用户交互数据 (数据增强)'

    def handle(self, *args, **options):
        # 1. 确保有用户
        users = User.objects.all()
        if not users.exists():
            self.stdout.write("未找到任何用户，开始创建测试用户...")
            User.objects.create_user(username='tester1', password='password')
            users = User.objects.filter(username='tester1')
        
        # 2. 找出动作
        exercises = list(Exercise.objects.all())
        if len(exercises) < 5:
            self.stdout.write(self.style.ERROR("动作数量太少，请先运行 generate_progression 补全动作！"))
            return

        self.stdout.write(f"正在为 {len(users)} 个用户生成模拟数据...")

        # 对于每个肌群，生成一些模拟练习记录
        muscle_groups = {}
        for ex in exercises:
            if ex.target_muscle not in muscle_groups:
                muscle_groups[ex.target_muscle] = []
            muscle_groups[ex.target_muscle].append(ex)

        interactions_count = 0
        for user in users:
            # 模拟 5-10 个训练日
            for _ in range(random.randint(5, 10)):
                training_day = timezone.now() - timedelta(days=random.randint(0, 30))
                
                # 随机选择一个肌群进行训练
                muscle = random.choice(list(muscle_groups.keys()))
                group = sorted(muscle_groups[muscle], key=lambda x: x.level)
                
                # 模拟一个训练 Session (连续做 3-5 个动作)
                num_to_train = random.randint(3, min(len(group), 5))
                current_time = training_day
                
                for i in range(num_to_train):
                    ex = group[i]
                    # 模拟完成记录
                    UserExerciseRecord.objects.create(
                        user=user,
                        exercise=ex,
                        count=random.randint(10, 30),
                        duration=random.randint(60, 300),
                        accuracy_score=random.uniform(70, 95),
                        calories_burned=random.uniform(20, 100),
                        created_at=current_time
                    )
                    
                    # 模拟实时交互记录
                    UserInteraction.objects.create(
                        user=user,
                        exercise=ex,
                        interaction_type='finish',
                        score=random.uniform(0.7, 1.0),
                        timestamp=current_time
                    )
                    
                    # 同一个 Session，每个动作间隔 15-30 分钟
                    current_time += timedelta(minutes=random.randint(15, 30))
                    interactions_count += 2

        self.stdout.write(self.style.SUCCESS(f"模拟数据补全完成，共生成 {interactions_count} 条记录！"))
        self.stdout.write("请再执行 sync_knowledge_graph_data 建立图谱关联。")
