from django.db import models
from django.contrib.auth.models import User
from django.db.models.signals import post_save
from django.dispatch import receiver

# --- 表1: 用户详细档案 (UserProfile) ---
class UserProfile(models.Model):
    # 1. 关联核心账号 (一对一: 一个账号只能有一份档案)
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='profile')
    
    # 2. 基础数据
    nickname = models.CharField("昵称", max_length=50, blank=True)
    gender = models.CharField("性别", max_length=10, choices=[('male', '男'), ('female', '女')], default='male')
    age = models.IntegerField("年龄", default=20)
    height = models.FloatField("身高 (cm)", default=170.0)
    weight = models.FloatField("体重 (kg)", default=65.0)
    
    # 3. 进阶数据 (伤病史等，AI 生成计划需要)
    injury_history = models.TextField("伤病史", blank=True, default="无")
    fitness_level = models.CharField("运动基础", max_length=20, default="beginner", 
                                     choices=[('beginner', '新手'), ('intermediate', '进阶'), ('advanced', '大神')])

    def __str__(self):
        return f"{self.user.username} 的档案"

# --- 信号机制: 自动创建档案 ---
# 作用: 当你在注册页面创建 User 时，Django 会自动在这里也创建一行空的 UserProfile
@receiver(post_save, sender=User)
def create_user_profile(sender, instance, created, **kwargs):
    if created:
        UserProfile.objects.create(user=instance)

@receiver(post_save, sender=User)
def save_user_profile(sender, instance, **kwargs):
    instance.profile.save()

# --- 表2: 训练记录 (TrainingLog) ---
class TrainingLog(models.Model):
    # 关联用户 (一对多: 一个用户可以有很多条记录)
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='logs')
    
    action_name = models.CharField("动作名称", max_length=50) # 例如 "深蹲"
    count = models.IntegerField("完成数量", default=0)
    duration = models.IntegerField("耗时(秒)", default=0)
    accuracy_score = models.FloatField("AI评分", default=0.0) 
    calories = models.FloatField("消耗卡路里", default=0.0)
    
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.user.username} - {self.action_name} ({self.created_at.date()})"