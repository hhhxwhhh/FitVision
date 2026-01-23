from django.contrib import admin
from .models import ExerciseCategory, Exercise, UserExerciseRecord

@admin.register(ExerciseCategory)
class ExerciseCategoryAdmin(admin.ModelAdmin):
    list_display = ('name', 'order', 'is_active', 'created_at')
    list_filter = ('is_active', 'created_at')
    search_fields = ('name', 'description')
    ordering = ('order',)


@admin.register(Exercise)
class ExerciseAdmin(admin.ModelAdmin):
    list_display = ('name', 'category', 'difficulty', 'target_muscle', 'is_active', 'order')
    list_filter = ('category', 'difficulty', 'target_muscle', 'equipment', 'is_active')
    search_fields = ('name', 'english_name', 'description')
    ordering = ('order', 'name')

    # 👇 新增：使用 fieldsets 对字段进行漂亮的分组
    fieldsets = (
        ('基本信息', {
            'fields': ('name', 'english_name', 'category', 'description')
        }),
        ('演示教学 (GIF)', {
            'fields': ('demo_gif',),  # 👈 哪怕你之前的名字写错了，只要这里写对，就能显示！
        }),
        ('训练参数', {
            'fields': ('difficulty', 'target_muscle', 'equipment')
        }),
        ('系统设置', {
            'fields': ('is_active', 'order'),
            'classes': ('collapse',),  #这一行可以让这个区域默认折叠
        }),
        # ⚠️ 重要提示：
        # 如果你的模型里还有 "steps"(动作要领) 或 "notes"(注意事项) 等字段
        # 请务必把它们也加进来，否则保存时会消失！例如：
        # ('详细指导', {
        #     'fields': ('steps', 'notes') 
        # }),
    )


@admin.register(UserExerciseRecord)
class UserExerciseRecordAdmin(admin.ModelAdmin):
    list_display = ('user', 'exercise', 'count', 'accuracy_score', 'calories_burned', 'created_at')
    list_filter = ('exercise', 'created_at')
    search_fields = ('user__username', 'exercise__name')
    readonly_fields = ('created_at',)