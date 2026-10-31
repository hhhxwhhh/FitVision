import random
from django.core.management.base import BaseCommand
from django.contrib.auth.models import User
from django.utils import timezone
from datetime import timedelta
from exercises.models import Exercise
from recommendations.models import UserInteraction

class Command(BaseCommand):
    help = '随机生成用户练习交互数据以供推荐系统训练'

    def add_arguments(self, parser):
        parser.add_argument('--users', type=int, default=10, help='生成多少个虚构用户的历史')
        parser.add_argument('--days', type=int, default=30, help='追溯多少天的历史')

    def handle(self, *args, **options):
        num_users = options['users']
        num_days = options['days']
        
        exercises = list(Exercise.objects.all())
        if not exercises:
            self.stdout.write(self.style.ERROR('数据库中没有动作数据，请先运行 generate_test_data.py'))
            return

        # 确保有一些用户
        users = list(User.objects.filter(is_superuser=False)[:num_users])
        if len(users) < num_users:
            for i in range(len(users), num_users):
                u = User.objects.create_user(username=f'dummy_user_{i}', password='password123')
                users.append(u)

        self.stdout.write(f'开始为 {len(users)} 个用户生成过去 {num_days} 天的历史轨迹...')

        interaction_count = 0
        for user in users:
            # 模拟每个用户有不同的活跃度
            activity_level = random.randint(3, 15) # 过去30天完成了多少次练习
            
            # 生成一个随机的时间序列
            start_date = timezone.now() - timedelta(days=num_days)
            
            # 为该用户生成一段有逻辑的动作序列（模拟真实训练习惯）
            # 比如：倾向于练某个部位，或者循序渐进
            preferred_muscle = random.choice(['chest', 'back', 'legs', 'abs'])
            filtered_exercises = [e for e in exercises if e.target_muscle == preferred_muscle or random.random() > 0.7]

            for _ in range(activity_level):
                # 随机选择 3-8 个动作构成一次完整的训练（Session）
                session_len = random.randint(3, 8)
                session_exercises = random.sample(filtered_exercises, min(len(filtered_exercises), session_len))
                
                # 随机一个训练时间
                session_time = start_date + timedelta(days=random.randint(0, num_days), hours=random.randint(6, 22))
                
                for i, ex in enumerate(session_exercises):
                    # 每个动作之间间隔几分钟
                    timestamp = session_time + timedelta(minutes=i * 10)
                    
                    # 创建完成记录
                    UserInteraction.objects.create(
                        user=user,
                        exercise=ex,
                        interaction_type='finish',
                        score=1.0,
                    )
                    # 强行修改 auto_now_add 的时间（仅用于模拟历史数据）
                    UserInteraction.objects.filter(user=user, exercise=ex).update(timestamp=timestamp)
                    
                    interaction_count += 1
                    
                    # 偶尔点个赞
                    if random.random() > 0.8:
                        UserInteraction.objects.create(
                            user=user,
                            exercise=ex,
                            interaction_type='like',
                            score=1.0,
                        )
                    # 偶尔跳过一些不喜欢的
                    elif random.random() > 0.95:
                        UserInteraction.objects.create(
                            user=user,
                            exercise=ex,
                            interaction_type='skip',
                            score=-0.5,
                        )

        self.stdout.write(self.style.SUCCESS(f'成功生成了 {interaction_count} 条模拟交互数据！'))
        self.stdout.write(self.style.SUCCESS('现在你可以运行 python manage.py process_rec_data 来准备训练数据了。'))
