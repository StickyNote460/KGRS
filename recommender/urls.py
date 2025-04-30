# recommender/urls.py（新建应用级）
from django.urls import path #导入 Django 的 path 函数，用于定义 URL 模式
from . import views #从当前目录（.）导入 views 模块,使用同一目录下的 views.py 文件中定义的视图函数。

#设置了该应用的命名空间。
# 通过设置 app_name，可以在模板或代码中使用命名空间来反向解析 URL，
# 避免不同应用之间的 URL 名称冲突
app_name = 'recommender'

urlpatterns = [
    path('', views.home, name='home'),
    path('courses/<str:pk>/', views.course_detail, name='course-detail'),
    path('users/<str:pk>/', views.user_profile, name='user-profile'),
]