from django.db import models
from django.contrib.auth.models import User

class ExerciseCategory(models.Model):
    """动作分类模型"""
    name = models.CharField("分类名称", max_length=50, unique=True)
    description = models.TextField("分类描述", blank=True)
    icon = models.CharField("图标", max_length=100, blank=True, help_text="分类图标标识")
    order = models.IntegerField("排序", default=0, help_text="显示顺序，数值越小越靠前")
    is_active = models.BooleanField("是否启用", default=True)
    created_at = models.DateTimeField("创建时间", auto_now_add=True)
    updated_at = models.DateTimeField("更新时间", auto_now=True)

    class Meta:
        verbose_name = "动作分类"
        verbose_name_plural = "动作分类"
        ordering = ['order']

    def __str__(self):
        return self.name


class Exercise(models.Model):
    """动作模型"""
    DIFFICULTY_CHOICES = [
        ('beginner', '入门'),
        ('intermediate', '中级'),
        ('advanced', '高级'),
    ]

    EQUIPMENT_CHOICES = [
        ('none', '无器械'),
        ('dumbbell', '哑铃'),
        ('barbell', '杠铃'),
        ('resistance_band', '阻力带'),
        ('kettlebell', '壶铃'),
        ('machine', '器械'),
        ('other', '其他'),
    ]

    TARGET_MUSCLE_CHOICES = [
        ('chest', '胸部'),
        ('back', '背部'),
        ('shoulders', '肩部'),
        ('arms', '手臂'),
        ('abs', '腹部'),
        ('legs', '腿部'),
        ('glutes', '臀部'),
        ('full_body', '全身'),
    ]

    # 基本信息
    name = models.CharField("动作名称", max_length=100, unique=True)
    english_name = models.CharField("英文名称", max_length=100, blank=True)
    description = models.TextField("动作描述")
    category = models.ForeignKey(
        ExerciseCategory, 
        on_delete=models.SET_NULL, 
        null=True, 
        blank=True, 
        verbose_name="动作分类"
    )
    
    # 难度和设备
    difficulty = models.CharField("难度等级", max_length=20, choices=DIFFICULTY_CHOICES, default='beginner')
    equipment = models.CharField("所需器材", max_length=30, choices=EQUIPMENT_CHOICES, default='none')
    target_muscle = models.CharField("目标肌群", max_length=20, choices=TARGET_MUSCLE_CHOICES)
    
    # 动作细节
    instructions = models.TextField("动作要领", help_text="详细的执行步骤")
    tips = models.TextField("注意事项", blank=True, help_text="安全提示和常见错误")
    video_url = models.URLField("教学视频链接", blank=True)
    image_url = models.URLField("动作图片链接", blank=True)
    
    # AI相关参数
    keypoints = models.JSONField("关键点坐标", blank=True, null=True, 
                                help_text="动作标准姿态的关键点坐标数据")
    angle_thresholds = models.JSONField("角度阈值", blank=True, null=True,
                                       help_text="各关节角度评判标准，如{'knee_min': 90}")
    correction_tips = models.JSONField("纠正提示", blank=True, null=True,
                                     help_text="常见错误及纠正方法，如{'knee_cave': '膝盖不要内扣'}")
    
    # 统计信息
    default_duration = models.IntegerField("默认时长(秒)", default=60, 
                                         help_text="建议的单次训练时长")
    default_reps = models.IntegerField("默认次数", default=10, 
                                      help_text="建议的单次训练次数")
    calories_burned = models.FloatField("每分钟消耗(卡路里)", default=5.0,
                                       help_text="每分钟平均消耗的卡路里")
    
    # 状态和排序
    is_active = models.BooleanField("是否启用", default=True)
    order = models.IntegerField("排序", default=0, help_text="显示顺序")
    created_at = models.DateTimeField("创建时间", auto_now_add=True)
    updated_at = models.DateTimeField("更新时间", auto_now=True)

    class Meta:
        verbose_name = "健身动作"
        verbose_name_plural = "健身动作"
        ordering = ['order', 'name']

    def __str__(self):
        return self.name


class UserExerciseRecord(models.Model):
    """用户动作练习记录模型（与用户模块关联）"""
    user = models.ForeignKey(User, on_delete=models.CASCADE, verbose_name="用户")
    exercise = models.ForeignKey(Exercise, on_delete=models.CASCADE, verbose_name="动作")
    
    # 练习结果
    count = models.IntegerField("完成次数", default=0)
    duration = models.IntegerField("训练时长(秒)", default=0)
    accuracy_score = models.FloatField("准确度评分", default=0.0, 
                                      help_text="AI评估的动作准确性(0-100)")
    calories_burned = models.FloatField("消耗卡路里", default=0.0)
    
    # 详细分析
    form_feedback = models.JSONField("动作反馈", blank=True, null=True,
                                    help_text="AI提供的详细动作分析")
    
    # 时间信息
    created_at = models.DateTimeField("创建时间", auto_now_add=True)

    class Meta:
        verbose_name = "用户动作记录"
        verbose_name_plural = "用户动作记录"
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.user.username} - {self.exercise.name} ({self.created_at.strftime('%Y-%m-%d')})"