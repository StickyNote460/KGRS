# recommender/signals.py
import logging
from django.db.models import Count
from django.db.models.signals import post_save, post_delete
from django.dispatch import receiver
from .models import UserCourse, Course, CourseConcept

logger = logging.getLogger(__name__)

@receiver([post_save, post_delete], sender=UserCourse)
def update_course_metrics_and_user_style(sender, instance, **kwargs):
    """同时更新课程热度和用户学习风格"""
    try:
        user = instance.user
        course = instance.course

        # ====== 更新课程热度 ======
        new_popularity = UserCourse.objects.filter(course=course).count()
        if course.popularity != new_popularity:
            course.popularity = new_popularity
            course.save(update_fields=['popularity'])
            logger.debug(f"更新课程 {course.id} 热度为 {new_popularity}")

        # ====== 更新用户学习风格 ======
        learned_concepts = CourseConcept.objects.filter(
            course__usercourse__user=user
        ).select_related('concept__field')

        field_stats = (
            learned_concepts
            .exclude(concept__field__isnull=True)
            .values('concept__field__name')
            .annotate(total=Count('concept__field'))
            .order_by('-total')
        )

        total_concepts = sum(item['total'] for item in field_stats)
        learning_style = {
            item['concept__field__name']: round(item['total'] / total_concepts, 3)
            for item in field_stats
        } if total_concepts > 0 else {}

        # ====== 直接更新用户的学习风格 ======
        user.learning_style = learning_style
        user.save(update_fields=['learning_style'])

        logger.debug(f"更新用户 {user.id} 学习风格: {learning_style}")

    except Exception as e:
        logger.error(f"更新课程或用户特征失败: {str(e)}", exc_info=True)
