from django.db.models.signals import post_save
from django.dispatch import receiver
from .models import UserCourse, PrerequisiteDependency

@receiver(post_save, sender=UserCourse)
def update_user_learning_style(sender, instance, **kwargs):
    """统一处理用户选课后的学习风格更新"""
    user = instance.user
    user.learning_style = user.calculate_learning_style()
    user.save()

@receiver(post_save, sender=PrerequisiteDependency)
def update_dependency_count(sender, instance, **kwargs):
    """更新先修关系计数"""
    prerequisite = instance.prerequisite
    prerequisite.dependency_count = prerequisite.required_by.count()
    prerequisite.save()