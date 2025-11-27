"""
URL configuration for fitvision project.
"""
from django.contrib import admin
# 1. 关键改动：这里必须导入 include 函数
from django.urls import path, include 
from django.http import JsonResponse
from drf_spectacular.views import SpectacularAPIView, SpectacularSwaggerView

# 这个测试接口可以留着，方便你验证服务器是不是活着
def simple_test_api(request):
    return JsonResponse({
        'message': 'hello from django rest framework backend',
        'status': 'success'
    })

urlpatterns = [
    path('admin/', admin.site.urls),
    
    # 保留测试接口
    path('api/test/', simple_test_api, name='simple_test_api'),

    # 2. 关键改动：添加这行！
    # 意思：凡是访问 /api/auth/ 开头的，全部转交给 users/urls.py 去处理
    path('api/auth/', include('users.urls')),
    
    # API文档
    path('api/schema/', SpectacularAPIView.as_view(), name='schema'),
    path('api/docs/', SpectacularSwaggerView.as_view(url_name='schema'), name='swagger-ui'),
]
