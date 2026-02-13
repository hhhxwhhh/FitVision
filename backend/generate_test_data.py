import os
import django

# 设置 Django 环境
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'fitvision.settings')
django.setup()

from django.contrib.auth.models import User
from exercises.models import Exercise, ExerciseCategory
from training.models import TrainingPlan, TrainingPlanDay, TrainingPlanExercise

def generate_data():
    # 1. 创建或获取测试用户
    user, created = User.objects.get_or_create(
        username='testuser',
        defaults={'is_staff': True, 'is_superuser': True}
    )
    if created:
        user.set_password('121623Ww')
        user.save()
        print(f"创建用户: {user.username}")

    # 2. 创建或获取动作分类
    cat_strength, _ = ExerciseCategory.objects.get_or_create(
        name='力量训练',
        defaults={'description': '提升肌肉力量的训练', 'icon': 'dumbbell'}
    )
    cat_cardio, _ = ExerciseCategory.objects.get_or_create(
        name='有氧训练',
        defaults={'description': '提升心肺功能的训练', 'icon': 'run'}
    )

    # 3. 创建测试动作
    pushup, _ = Exercise.objects.get_or_create(
        name='俯卧撑',
        defaults={
            'description': '经典的胸肌和三头肌训练',
            'category': cat_strength,
            'difficulty': 'beginner',
            'target_muscle': 'chest',
            'instructions': '双手略宽于肩，身体保持直线，下降至胸部接近地面，然后推起。'
        }
    )
    
    squat, _ = Exercise.objects.get_or_create(
        name='深蹲',
        defaults={
            'description': '下肢力量训练之王',
            'category': cat_strength,
            'difficulty': 'beginner',
            'target_muscle': 'legs',
            'instructions': '双脚与肩同宽，背部挺直，臀部后坐下蹲，直到大腿与地面平行。'
        }
    )

    jumping_jack, _ = Exercise.objects.get_or_create(
        name='开合跳',
        defaults={
            'description': '全身热身和有氧训练',
            'category': cat_cardio,
            'difficulty': 'beginner',
            'target_muscle': 'full_body',
            'instructions': '双脚并拢站立，跳起的同时双脚分开，手臂在头顶击掌，然后再跳回起始位置。'
        }
    )

    # 4. 创建训练计划
    plan, created = TrainingPlan.objects.get_or_create(
        name='7天新手居家塑形计划',
        created_by=user,
        defaults={
            'description': '专为新手设计的7天入门计划，无需器械，随时随地开启健身。',
            'goal': 'weight_loss',
            'difficulty': 'beginner',
            'duration_weeks': 1,
            'category': cat_strength,
            'estimated_calories_burned': 1500,
            'estimated_duration_minutes': 30,
            'is_public': True
        }
    )
    if created:
        print(f"创建计划: {plan.name}")

        # 5. 创建每日安排 (Day 1, Day 2, Day 3)
        # Day 1: 全身激活
        day1 = TrainingPlanDay.objects.create(
            plan=plan,
            day_number=1,
            title='全身初级激活',
            description='第一天，我们先从基础的全身动作开始。'
        )
        
        # 为 Day 1 添加动作
        TrainingPlanExercise.objects.create(training_day=day1, exercise=jumping_jack, sets=3, reps=20, order=1, notes='动作要连贯')
        TrainingPlanExercise.objects.create(training_day=day1, exercise=pushup, sets=3, reps=10, order=2, notes='如果觉得难可以跪姿俯卧撑')
        TrainingPlanExercise.objects.create(training_day=day1, exercise=squat, sets=3, reps=15, order=3)

        # Day 2: 休息
        TrainingPlanDay.objects.create(
            plan=plan,
            day_number=2,
            title='主动修复',
            is_rest_day=True,
            description='今天好好休息，或者做一些轻微的拉伸。'
        )

        # Day 3: 下肢增强
        day3 = TrainingPlanDay.objects.create(
            plan=plan,
            day_number=3,
            title='腿部力量增强',
            description='专注于下肢力量的提升。'
        )
        TrainingPlanExercise.objects.create(training_day=day3, exercise=squat, sets=4, reps=20, order=1)
        TrainingPlanExercise.objects.create(training_day=day3, exercise=jumping_jack, sets=3, reps=30, order=2)

        print("测试数据生成成功！")
    else:
        print("测试数据已存在，跳过生成。")

if __name__ == '__main__':
    generate_data()