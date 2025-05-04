from celery import shared_task
from .models import Course, Concept, CourseConcept

#直接遍历所有课程/概念在大数据量时会有性能问题，可以改为分批次处理
#小规模数据集上直接遍历应该问题不大，先不改了
@shared_task
def update_metrics():
    """更新所有指标"""
    # 更新课程热度
    for course in Course.objects.all():
        course.popularity = course.usercourse_set.count()
        course.save()

    # 更新概念权重
    for cc in CourseConcept.objects.all():
        cc.normalized_weight = cc.intelligent_weight
        cc.save()

#5.2 20:19新增
# recommender/tasks.py

# from celery import shared_task
# from .kg.build_kg import KnowledgeGraph
#
# @shared_task
# def rebuild_kg():
#     """重建知识图谱"""
#     kg = KnowledgeGraph()
#     kg.build()
#     kg.save_to_disk()
# @shared_task
# def update_course_popularity():
#     """更新课程热度"""
#     from .models import Course
#     for course in Course.objects.all():
#         course.popularity = course.usercourse_set.count()
#         course.save(update_fields=['popularity'])