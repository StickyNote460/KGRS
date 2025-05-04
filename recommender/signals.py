from django.db.models.signals import post_save
from django.dispatch import receiver
from .models import UserCourse, PrerequisiteDependency

#接收器（信号处理器)通过 @receiver 装饰器自动注册，但需要在 ready() 中导入信号模块。
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

"""5.2实现特征工程，构建知识图谱，完成推荐算法，新增"""
# recommender/signals.py
from django.db.models.signals import post_save, post_delete
from django.dispatch import receiver
from .models import (
    ParentSonRelation,
    PrerequisiteDependency,
    UserCourse
)
from .features.calculators.concept_calculators import DepthCalculator


@receiver([post_save, post_delete], sender=ParentSonRelation)
def update_hierarchy_depth(sender, instance, **kwargs):
    """更新概念层级深度"""

    def recursive_update(concept):
        new_depth = DepthCalculator.calculate_depth(concept)
        if concept.depth != new_depth:
            concept.depth = new_depth
            concept.save(update_fields=['depth'])
            # 递归更新子节点
            for child in concept.children.all():
                recursive_update(child.concept)

    recursive_update(instance.son)


@receiver(post_save, sender=PrerequisiteDependency)
def update_dependency_metrics(sender, instance, **kwargs):
    """更新被依赖次数指标"""
    prerequisite = instance.prerequisite
    prerequisite.dependency_count = prerequisite.required_by.count()
    prerequisite.save(update_fields=['dependency_count'])