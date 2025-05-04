import os
from celery import Celery
#`celery.py`文件是Celery与Django项目集成的核心配置文件，
# 负责初始化Celery应用、读取Django配置、自动发现任务，
# 并提供一个中央入口点来管理所有Celery相关的设置。


# 设置默认的 Django 设置模块，Celery需要知道Django的配置来正确初始化和集成。
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'KGRS.settings')
#创建了一个Celery应用实例，命名为`KGRS`。这个实例是Celery的核心，用于管理任务、配置等。
app = Celery('KGRS')
# 使用 Django 的 settings 文件配置 Celery
#从Django的`settings.py`中读取Celery的配置，配置项以`CELERY_`为命名空间。
app.config_from_object('django.conf:settings', namespace='CELERY')
# 自动发现所有 Django 应用中的 tasks.py
app.autodiscover_tasks()

#一个示例任务，用于调试目的。当调用这个任务时，它会打印请求信息。
@app.task(bind=True)
def debug_task(self):
    print(f'Request: {self.request!r}')