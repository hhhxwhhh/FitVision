from django.contrib import admin
from .models import AIAnalysisSession, AIModelConfig

@admin.register(AIAnalysisSession)
class AIAnalysisSessionAdmin(admin.ModelAdmin):
    list_display = ('record', 'processed_frames', 'average_confidence', 'analysis_time')
    search_fields = ('record__exercise__name',)

@admin.register(AIModelConfig)
class AIModelConfigAdmin(admin.ModelAdmin):
    list_display = ('exercise', 'model_version', 'is_active', 'created_at')
    list_filter = ('is_active',)
