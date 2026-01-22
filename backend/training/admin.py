from django.contrib import admin
from .models import TrainingPlan, TrainingPlanDay, TrainingPlanExercise, UserTrainingSession, UserTrainingExerciseRecord

@admin.register(TrainingPlan)
class TrainingPlanAdmin(admin.ModelAdmin):
    list_display = ('name', 'goal', 'difficulty', 'duration_weeks', 'is_public', 'is_active', 'created_by', 'created_at')
    list_filter = ('goal', 'difficulty', 'is_public', 'is_active', 'created_at')
    search_fields = ('name', 'description')
    ordering = ('-created_at',)


@admin.register(TrainingPlanDay)
class TrainingPlanDayAdmin(admin.ModelAdmin):
    list_display = ('plan', 'day_number', 'title', 'is_rest_day')
    list_filter = ('is_rest_day', 'plan')
    search_fields = ('title', 'description', 'plan__name')
    ordering = ('plan', 'day_number')


@admin.register(TrainingPlanExercise)
class TrainingPlanExerciseAdmin(admin.ModelAdmin):
    list_display = ('training_day', 'exercise', 'sets', 'reps', 'duration_seconds', 'order')
    list_filter = ('training_day__plan', 'exercise')
    search_fields = ('exercise__name', 'training_day__title')
    ordering = ('training_day', 'order')


@admin.register(UserTrainingSession)
class UserTrainingSessionAdmin(admin.ModelAdmin):
    list_display = ('user', 'plan', 'start_time', 'is_completed', 'performance_score')
    list_filter = ('is_completed', 'start_time', 'plan')
    search_fields = ('user__username', 'plan__name')
    readonly_fields = ('start_time',)


@admin.register(UserTrainingExerciseRecord)
class UserTrainingExerciseRecordAdmin(admin.ModelAdmin):
    list_display = ('session', 'exercise', 'sets_completed', 'form_score', 'created_at')
    list_filter = ('exercise', 'created_at', 'session__plan')
    search_fields = ('exercise__name', 'session__user__username')
    readonly_fields = ('created_at',)