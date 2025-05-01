import os
from celery import Celery
# 设置默认的 Django 设置模块
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'KGRS.settings')
app = Celery('KGRS')
# 使用 Django 的 settings 文件配置 Celery
app.config_from_object('django.conf:settings', namespace='CELERY')
# 自动发现所有 Django 应用中的 tasks.py
app.autodiscover_tasks()

@app.task(bind=True)
def debug_task(self):
    print(f'Request: {self.request!r}')