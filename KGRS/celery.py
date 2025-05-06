import os
from celery import Celery
#`celery.py`文件是Celery与Django项目集成的核心配置文件，
# 负责初始化Celery应用、读取Django配置、自动发现任务，
# 并提供一个中央入口点来管理所有Celery相关的设置。
"""
在celery.py中，创建celery应用实例，
并将其与Django项目绑定（读取settings.py里关于celery的配置，如时区，定时任务等）。
通过KGRS/__init__.py，把在celery.py里创建的应用实例导出，并命名为celery\_app。
就是把 Celery 应用实例暴露为模块级变量 celery_app。
Django启动完成__init__.py的执行。
开启worker时（就是运行 celery -A KGRS -l info)，
就会从配置目录KGRS里导入celery_app。
也就是绑定了Django项目的celery应用实例。
"""

# 设置默认的 Django 设置模块，Celery需要知道Django的配置来正确初始化和集成。
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'KGRS.settings')

#创建了一个Celery应用实例，命名为`KGRS`。这个实例是Celery的核心，用于管理任务、配置等。
'''
这里的KGRS只是一个命名标识符，Celery 会用它来标记这个应用
不必须和项目同名
同名主要是考虑到清晰规范和一致性。
当运行命令启动worker时： celery -A KGRS worker -l info
-A KGRS中的KGRS会被解析为：from KGRS import celery_app
这里的KGRS就是项目的同名配置目录
'''
app = Celery('KGRS')

# 使用 Django 的 settings 文件配置 Celery
#从Django的`settings.py`中读取Celery的配置，配置项以`CELERY_`为命名空间。
#就是从 Django 的 settings.py 中加载以 CELERY_ 开头的配置项。
#将这些配置应用到 Celery 应用实例 app 中
app.config_from_object('django.conf:settings', namespace='CELERY')

# 自动发现所有 Django 应用中的 tasks.py
app.autodiscover_tasks()

#一个示例任务，用于调试目的。当调用这个任务时，它会打印请求信息。
@app.task(bind=True)
def debug_task(self):
    print(f'Request: {self.request!r}')