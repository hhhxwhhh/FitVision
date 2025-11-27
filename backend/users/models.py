from django.db import models
from django.contrib.auth.models import User
from django.db.models.signals import post_save
from django.dispatch import receiver

class UserProfile(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='profile')
    nickname = models.CharField("昵称", max_length=50, blank=True)
    gender = models.CharField("性别", max_length=10, choices=[('male', '男'), ('female', '女')], default='male')
    age = models.IntegerField("年龄", default=20)
    height = models.FloatField("身高 (cm)", default=170.0)
    weight = models.FloatField("体重 (kg)", default=65.0)
    injury_history = models.TextField("伤病史", blank=True, default="无")
    fitness_level = models.CharField("运动基础", max_length=20, default="beginner", 
                                     choices=[('beginner', '新手'), ('intermediate', '进阶'), ('advanced', '大神')])

    def __str__(self):
        return f"{self.user.username} 的档案"

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