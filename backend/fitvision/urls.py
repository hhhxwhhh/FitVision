"""
URL configuration for fitvision project.
"""
from django.contrib import admin
from django.urls import path, include 
from django.conf import settings
from django.conf.urls.static import static
from django.http import JsonResponse
from drf_spectacular.views import SpectacularAPIView, SpectacularSwaggerView

def simple_test_api(request):
    return JsonResponse({
        'message': 'hello from django rest framework backend',
        'status': 'success'
    })

urlpatterns = [
    path('admin/', admin.site.urls),
    
    path('api/test/', simple_test_api, name='simple_test_api'),
    path('api/auth/', include('users.urls')),
    path('api/exercises/', include('exercises.urls')),
    path('api/training/', include('training.urls')),
    path('api/ai/', include('ai_models.urls')),
    path('api/analytics/', include('analytics.urls')),
    
    # API文档
    path('api/schema/', SpectacularAPIView.as_view(), name='schema'),
    path('api/docs/', SpectacularSwaggerView.as_view(url_name='schema'), name='swagger-ui'),
]

# 🔥 新增：在开发模式下服务媒体文件
if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)