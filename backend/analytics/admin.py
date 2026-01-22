from django.contrib import admin
from .models import UserDailyStats, UserBodyMetric, ExerciseProgress

@admin.register(UserDailyStats)
class UserDailyStatsAdmin(admin.ModelAdmin):
    list_display = ('user', 'date', 'total_duration_minutes', 'total_calories_burned', 'average_form_score')
    list_filter = ('date', 'user')

@admin.register(UserBodyMetric)
class UserBodyMetricAdmin(admin.ModelAdmin):
    list_display = ('user', 'date', 'weight', 'bmi')
    list_filter = ('user',)

@admin.register(ExerciseProgress)
class ExerciseProgressAdmin(admin.ModelAdmin):
    list_display = ('user', 'exercise', 'date', 'max_weight', 'best_form_score')
    list_filter = ('exercise', 'user')
