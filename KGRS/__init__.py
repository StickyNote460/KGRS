# KGRS/__init__.py

#从当前模块 KGRS/celery.py 中导入 Celery 应用实例 app，并把它命名为 celery_app
#确保当 Django 项目被导入或启动时，Celery 应用也会被初始化。
from .celery import app as celery_app

#定义模块的“公开接口”。当其他模块执行 from KGRS import * 时，只导入 celery_app
__all__ = ('celery_app',)
