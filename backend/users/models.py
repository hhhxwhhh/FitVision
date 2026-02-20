from django.db import models
from django.contrib.auth.models import User
from django.db.models.signals import post_save
from django.dispatch import receiver
from exercises.models import Exercise

class UserProfile(models.Model):
    ACTIVITY_LEVEL_CHOICES = [
        ('sedentary', '久坐不动'),
        ('light', '轻度活动'),
        ('moderate', '中度活动'),
        ('active', '高度活动'),
        ('very_active', '极高活动'),
    ]
    
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='profile')
    avatar = models.ImageField("头像", upload_to='avatars/', null=True, blank=True)
    nickname = models.CharField("昵称", max_length=50, blank=True)
    gender = models.CharField("性别", max_length=10, choices=[('male', '男'), ('female', '女')], default='male')
    age = models.IntegerField("年龄", default=20)
    height = models.FloatField("身高 (cm)", default=170.0)
    weight = models.FloatField("体重 (kg)", default=65.0)
    injury_history = models.TextField("伤病史", blank=True, default="无")
    fitness_level = models.CharField("运动基础", max_length=20, default="beginner", 
                                     choices=[('beginner', '新手'), ('intermediate', '进阶'), ('advanced', '大神')])
    
    # 新增字段
    activity_level = models.CharField("日常活动水平", max_length=20, choices=ACTIVITY_LEVEL_CHOICES, default='moderate')
    target_weight = models.FloatField("目标体重 (kg)", null=True, blank=True)
    target_date = models.DateField("目标达成日期", null=True, blank=True)
    daily_calorie_intake = models.IntegerField("每日摄入热量目标 (卡路里)", null=True, blank=True)
    daily_calorie_burn = models.IntegerField("每日消耗热量目标 (卡路里)", null=True, blank=True)
    
    # 身体指标
    bmi = models.FloatField("BMI", null=True, blank=True)
    bmr = models.FloatField("基础代谢率", null=True, blank=True)
    
    created_at = models.DateTimeField("创建时间", auto_now_add=True)
    updated_at = models.DateTimeField("更新时间", auto_now=True)

    def __str__(self):
        return f"{self.user.username} 的档案"

    def save(self, *args, **kwargs):
        # 计算BMI和BMR
        if self.height and self.weight:
            self.bmi = self.weight / ((self.height / 100) ** 2)
            
            # 计算BMR (基础代谢率) - Mifflin-St Jeor 方程
            if self.gender == 'male':
                self.bmr = 10 * self.weight + 6.25 * self.height - 5 * self.age + 5
            else:
                self.bmr = 10 * self.weight + 6.25 * self.height - 5 * self.age - 161
                
        super().save(*args, **kwargs)

@receiver(post_save, sender=User)
def create_user_profile(sender, instance, created, **kwargs):
    if created:
        UserProfile.objects.create(user=instance)

@receiver(post_save, sender=User)
def save_user_profile(sender, instance, **kwargs):
    instance.profile.save()

class TrainingLog(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='logs')
    action_name = models.CharField("动作名称", max_length=50)
    count = models.IntegerField("完成数量", default=0)
    duration = models.IntegerField("耗时(秒)", default=0)
    accuracy_score = models.FloatField("AI评分", default=0.0) 
    calories = models.FloatField("消耗卡路里", default=0.0)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.user.username} - {self.action_name} ({self.created_at.date()})"

class UserGoal(models.Model):
    GOAL_TYPE_CHOICES = [
        ('weight_loss', '减重'),
        ('muscle_gain', '增肌'),
        ('fitness', '健身'),
        ('endurance', '耐力提升'),
    ]
    
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='goals')
    goal_type = models.CharField("目标类型", max_length=20, choices=GOAL_TYPE_CHOICES)
    target_value = models.FloatField("目标值")
    current_value = models.FloatField("当前值", default=0)
    start_date = models.DateField("开始日期")
    target_date = models.DateField("目标日期")
    is_active = models.BooleanField("是否激活", default=True)
    achieved = models.BooleanField("是否达成", default=False)
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        verbose_name = "用户目标"
        verbose_name_plural = "用户目标"
    
    def __str__(self):
        return f"{self.user.username} - {self.get_goal_type_display()} 目标"

class UserStats(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='stats')
    
    # 总体统计
    total_trainings = models.IntegerField("总训练次数", default=0)
    total_training_days = models.IntegerField("总训练天数", default=0)
    total_training_time = models.IntegerField("总训练时长(分钟)", default=0)
    total_calories_burned = models.FloatField("总消耗卡路里", default=0.0)
    
    # 最佳记录
    best_accuracy_score = models.FloatField("最佳动作准确度", default=0.0)
    longest_training_streak = models.IntegerField("最长连续训练天数", default=0)
    
    # 周/月统计
    weekly_trainings = models.IntegerField("本周训练次数", default=0)
    monthly_trainings = models.IntegerField("本月训练次数", default=0)
    
    last_updated = models.DateTimeField(auto_now=True)
    
    class Meta:
        verbose_name = "用户统计数据"
        verbose_name_plural = "用户统计数据"
    
    def __str__(self):
        return f"{self.user.username} 的统计数据"

@receiver(post_save, sender=User)
def create_user_stats(sender, instance, created, **kwargs):
    if created:
        UserStats.objects.create(user=instance)