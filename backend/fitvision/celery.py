import os
from celery import Celery

# 设置 Django 设置模块
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'fitvision.settings')

app = Celery('fitvision')

# 使用 Django 设置文件中的配置
app.config_from_object('django.conf:settings', namespace='CELERY')

# 自动发现任务
app.autodiscover_tasks()