"""
URL configuration for fitvision project.
"""
from django.contrib import admin
from django.urls import path, include 
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
    
    # API文档
    path('api/schema/', SpectacularAPIView.as_view(), name='schema'),
    path('api/docs/', SpectacularSwaggerView.as_view(url_name='schema'), name='swagger-ui'),
]