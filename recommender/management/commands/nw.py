# recommender/management/commands/nw.py
import os
import django
import logging
from django.db import models
from tqdm import tqdm
from collections import defaultdict
from recommender.models import CourseConcept, Concept, Course

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'KGRS.settings')
django.setup()

logger = logging.getLogger(__name__)


class WeightCalculator:
    """
    增强版归一化权重计算器
    算法版本: 2.0
    """

    def __init__(self):
        self._precompute_global_factors()
        self._precompute_course_factors()

    def calculate_weights(self):
        """主计算流程"""
        cc_relations = CourseConcept.objects.select_related(
            'concept', 'course'
        ).prefetch_related('course__concepts')

        batch = []
        for cc in tqdm(cc_relations, desc="处理课程-概念关系"):
            try:
                weight = self._calculate_single_weight(cc)
                cc.normalized_weight = weight
                batch.append(cc)

                if len(batch) >= 1000:
                    self._bulk_update(batch)
                    batch = []

            except Exception as e:
                logger.error(f"计算失败 Course:{cc.course.id} Concept:{cc.concept.id} - {str(e)}")

        if batch:
            self._bulk_update(batch)

    def _calculate_single_weight(self, cc):
        """单个课程-概念权重计算"""
        # 全局因子（35%）
        global_factor = (
                0.6 * self.global_importance.get(cc.concept.id, 0) +
                0.4 * self.dependency_factor.get(cc.concept.id, 0)
        )

        # 课程上下文因子（50%）
        context_factor = (
                0.4 * self._get_video_tfidf(cc) +
                0.3 * self._get_course_frequency(cc) +
                0.3 * self._get_difficulty_factor(cc.course)
        )

        # 时序因子（15%）
        time_factor = self._get_temporal_factor(cc.course)

        return min(0.35 * global_factor + 0.5 * context_factor + 0.15 * time_factor, 1.0)

    def _precompute_global_factors(self):
        """预计算全局指标"""
        # 概念全局重要性（标准化到0-1）
        all_concepts = Concept.objects.annotate(
            dep_count=models.F('dependency_count'),
            inv_depth=1.0 / (models.F('depth') + 1)
        ).values('id', 'dep_count', 'inv_depth')

        max_dep = max(c['dep_count'] for c in all_concepts) or 1
        max_inv_depth = max(c['inv_depth'] for c in all_concepts) or 1

        self.global_importance = {
            c['id']: (0.7 * (c['dep_count'] / max_dep) + 0.3 * (c['inv_depth'] / max_inv_depth))
            for c in all_concepts
        }

        # 被依赖网络中心性（简化版）
        deps = PrerequisiteDependency.objects.values_list('prerequisite', 'target')
        dependency_graph = defaultdict(list)
        for pre, target in deps:
            dependency_graph[pre].append(target)

        self.dependency_factor = {
            c.id: len(dependency_graph.get(c.id, []))
            for c in Concept.objects.all()
        }
        max_dep_factor = max(self.dependency_factor.values()) or 1
        self.dependency_factor = {k: v / max_dep_factor for k, v in self.dependency_factor.items()}

    def _precompute_course_factors(self):
        """预计算课程级指标"""
        # TF-IDF词典
        self.tfidf = defaultdict(float)
        all_courses = Course.objects.exclude(video_name__len=0)

        # 计算DF（包含某概念的课程数）
        concept_df = defaultdict(int)
        total_courses = all_courses.count()
        for course in all_courses:
            for name in course.video_name:
                for concept in Concept.objects.filter(name__icontains=name):
                    concept_df[concept.id] += 1

        # 计算TF-IDF
        for course in all_courses:
            total_words = len(course.video_name)
            concept_tf = defaultdict(int)
            for name in course.video_name:
                for concept in Concept.objects.filter(name__icontains=name):
                    concept_tf[concept.id] += 1

            for cid, tf in concept_tf.items():
                idf = math.log(total_courses / (1 + concept_df[cid]))
                self.tfidf[(course.id, cid)] = (tf / total_words) * idf

    def _get_video_tfidf(self, cc):
        """获取视频TF-IDF分数"""
        return self.tfidf.get((cc.course.id, cc.concept.id), 0)

    def _get_course_frequency(self, cc):
        """课程内频率因子"""
        total = cc.course.concepts.count()
        return cc.course.courseconcept_set.filter(concept=cc.concept).count() / total if total else 0

    def _get_difficulty_factor(self, course):
        """课程难度调整因子"""
        return min(course.difficulty / 5.0, 1.0)  # 假设难度最大为5

    def _get_temporal_factor(self, course):
        """时序因子（示例）"""
        # 假设课程有更新时间字段，越新权重越高
        if hasattr(course, 'update_time'):
            days_old = (timezone.now() - course.update_time).days
            return 1.0 / (1 + math.log1p(days_old))
        return 0.8  # 默认值

    def _bulk_update(self, batch):
        """批量更新"""
        CourseConcept.objects.bulk_update(batch, ['normalized_weight'])
        logger.info(f"已批量更新{len(batch)}条记录")


class Command(BaseCommand):
    help = "计算课程-概念归一化权重（增强版）"

    def handle(self, *args, **options):
        calculator = WeightCalculator()
        calculator.calculate_weights()
        self.stdout.write(self.style.SUCCESS("✓ 归一化权重计算完成"))