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


@admin.register(UserExerciseRecord)
class UserExerciseRecordAdmin(admin.ModelAdmin):
    list_display = ('user', 'exercise', 'count', 'accuracy_score', 'calories_burned', 'created_at')
    list_filter = ('exercise', 'created_at')
    search_fields = ('user__username', 'exercise__name')
    readonly_fields = ('created_at',)