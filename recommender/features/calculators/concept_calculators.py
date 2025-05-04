# recommender/features/calculators/concept_calculators.py
from django.db.models import Max, Count
from recommender.models import Concept

class DepthCalculator:
    @classmethod
    def calculate_depth(cls, concept):
        """递归计算概念的最大层级深度"""
        if not concept.parents.exists():
            return 0
        return 1 + max(
            [cls.calculate_depth(parent) for parent in concept.parents.all()]
        )

class ConceptImportanceCalculator:
    @classmethod
    def calculate_normalized_importance(cls):
        """批量计算概念重要性（归一化0-1）"""
        max_count = Concept.objects.aggregate(max=Max('dependency_count'))['max'] or 1
        for concept in Concept.objects.all():
            concept.normalized_importance = concept.dependency_count / max_count
            concept.save(update_fields=['normalized_importance'])

