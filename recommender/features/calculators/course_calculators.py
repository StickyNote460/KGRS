# recommender/features/calculators/course_calculators.py
from django.db.models import Avg
from recommender.models import Course

class CourseDifficultyCalculator:
    @classmethod
    def calculate_difficulty(cls, course):
        """基于关联概念的平均深度计算难度"""
        avg_depth = course.concepts.aggregate(avg=Avg('depth'))['avg'] or 1.0
        return round(avg_depth, 2)
