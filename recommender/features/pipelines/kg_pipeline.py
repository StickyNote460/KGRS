# recommender/features/pipelines/kg_pipeline.py
from celery import shared_task
from recommender.features.calculators.course_calculators import CourseDifficultyCalculator
from recommender.features.calculators.concept_calculators import DepthCalculator,ConceptImportanceCalculator
from recommender.models import Concept, Course


@shared_task
def full_kg_feature_pipeline():
    """全量特征计算流水线"""
    # 1. 概念特征
    for concept in Concept.objects.all():
        concept.depth = DepthCalculator.calculate_depth(concept)
        concept.save(update_fields=['depth'])

    ConceptImportanceCalculator.calculate_normalized_importance()

    # 2. 课程特征
    for course in Course.objects.all():
        course.difficulty = CourseDifficultyCalculator.calculate_difficulty(course)
        course.save(update_fields=['difficulty'])