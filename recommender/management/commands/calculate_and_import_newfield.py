# recommender/management/commands/calculate_all_fields.py
# 如果出现以下报错，就需要添加前四行导入，Django环境初始化
# django.core.exceptions.ImproperlyConfigured:
# Requested setting INSTALLED_APPS, but settings are not configured.
# You must either define the environment variable DJANGO_SETTINGS_MODULE
# or call settings.configure() before accessing settings.
import os
import django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'KGRS.settings')
django.setup()

import logging
from django.core.management.base import BaseCommand
from django.db import transaction, models
from tqdm import tqdm
import json
from collections import defaultdict
from recommender.models import (
    Concept,
    ParentSonRelation,
    PrerequisiteDependency,
    Course,
    User,
    CourseConcept
)

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = "批量计算并更新所有衍生字段数据"

    def handle(self, *args, **options):
        try:
            with transaction.atomic():
                self._calculate_concept_depth()
                self._calculate_dependency_count()
                self._calculate_course_metrics()
                self._calculate_user_styles()
                self._calculate_normalized_weights()
        except Exception as e:
            logger.error(f"批量计算失败: {str(e)}")
            raise

    # -------------------- 概念深度计算 --------------------
    #parentson中指明的关系树其实不高，基本就三层，所以采用深度优先搜索会更快，但实际情况中采用广度优先或许会更好
    '''
    使用深度优先搜索(DFS)策略
    采用递归方式遍历概念层级
    使用processed集合避免重复处理
    包含进度显示（使用tqdm）
    '''
    def _calculate_concept_depth(self):
        """计算概念层级深度"""
        try:
            self.stdout.write("\n[阶段1/5] 正在计算概念深度...")

            # 初始化所有深度为0
            Concept.objects.update(depth=0)

            # 构建父子关系映射
            children_map = defaultdict(list)
            for rel in tqdm(
                    ParentSonRelation.objects.all(),
                    desc="构建关系图",
                    unit="relations"
            ):
                children_map[rel.parent_id].append(rel.son_id)

            # 递归计算深度
            processed = set()

            def _recursive_depth(concept_id, current_depth):
                if concept_id in processed:
                    return

                concept = Concept.objects.get(id=concept_id)
                if concept.depth < current_depth:
                    concept.depth = current_depth
                    concept.save()

                processed.add(concept_id)
                for child_id in children_map.get(concept_id, []):
                    _recursive_depth(child_id, current_depth + 1)

            # 查找根节点（没有父节点的概念）
            root_ids = set(Concept.objects.values_list('id', flat=True)) - \
                       set(ParentSonRelation.objects.values_list('son_id', flat=True))

            for root_id in tqdm(root_ids, desc="处理根节点"):
                _recursive_depth(root_id, 1)

            self.stdout.write(self.style.SUCCESS("✓ 概念深度计算完成"))

        except Exception as e:
            logger.error(f"概念深度计算失败: {str(e)}")
            raise

    '''
        使用广度优先搜索(BFS)策略
        采用队列实现的迭代方式
        不需要额外的processed集合（通过深度比较隐式避免重复）
        避免了递归的栈溢出风险
        内存使用更可控（队列虽然可能大，但不会像递归那样指数增长）
        代码结构更简单，没有嵌套函数
        适合广度优先的场景
        '''

    # def _calculate_concept_depth(self):
    #     """使用非递归方式计算深度"""
    #     try:
    #         self.stdout.write("\n[阶段1/5] 正在计算概念深度...")
    #
    #         # 使用迭代代替递归
    #         from collections import deque
    #
    #         Concept.objects.update(depth=0)
    #         children_map = defaultdict(list)
    #         for rel in ParentSonRelation.objects.all():
    #             children_map[rel.parent_id].append(rel.son_id)
    #
    #         # 查找根节点
    #         all_concepts = set(Concept.objects.values_list('id', flat=True))
    #         has_parent = set(ParentSonRelation.objects.values_list('son_id', flat=True))
    #         roots = all_concepts - has_parent
    #
    #         # 广度优先遍历
    #         queue = deque()
    #         for root_id in roots:
    #             queue.append((root_id, 1))
    #
    #         while queue:
    #             concept_id, depth = queue.popleft()
    #             concept = Concept.objects.get(id=concept_id)
    #             if concept.depth < depth:
    #                 concept.depth = depth
    #                 concept.save()
    #
    #             for child_id in children_map.get(concept_id, []):
    #                 queue.append((child_id, depth + 1))
    #
    #         self.stdout.write(self.style.SUCCESS("✓ 概念深度计算完成"))
    #
    #     except Exception as e:
    #         logger.error(f"概念深度计算失败: {str(e)}")
    #         raise

    # -------------------- 被依赖次数计算 --------------------
    def _calculate_dependency_count(self):
        """分批次更新被依赖次数"""
        try:
            self.stdout.write("\n[阶段2/5] 正在计算被依赖次数...")

            # 分批次处理（每次1000条）
            batch_size = 1000
            dep_counts = PrerequisiteDependency.objects.values('prerequisite') \
                .annotate(count=models.Count('prerequisite'))

            for i in range(0, len(dep_counts), batch_size):
                batch = dep_counts[i:i + batch_size]
                update_map = {item['prerequisite']: item['count'] for item in batch}

                concepts = Concept.objects.filter(id__in=update_map.keys())
                for concept in concepts:
                    concept.dependency_count = update_map[concept.id]

                Concept.objects.bulk_update(
                    concepts,
                    ['dependency_count'],
                    batch_size=500
                )

            self.stdout.write(self.style.SUCCESS("✓ 被依赖次数计算完成"))

        except Exception as e:
            logger.error(f"被依赖次数计算失败: {str(e)}")
            raise
    # def _calculate_dependency_count(self):
    #     """计算概念被依赖次数"""
    #     try:
    #         self.stdout.write("\n[阶段2/5] 正在计算被依赖次数...")
    #
    #         # 批量统计依赖关系
    #         dep_counts = (
    #             PrerequisiteDependency.objects
    #             .values('prerequisite')
    #             .annotate(count=models.Count('prerequisite'))
    #         )
    #
    #         # 批量更新
    #         update_map = {item['prerequisite']: item['count'] for item in dep_counts}
    #         batch_size = 1000
    #
    #         concepts = list(Concept.objects.all())
    #         for concept in tqdm(concepts, desc="更新概念", unit="concepts"):
    #             concept.dependency_count = update_map.get(concept.id, 0)
    #
    #         Concept.objects.bulk_update(concepts, ['dependency_count'], batch_size)
    #         self.stdout.write(self.style.SUCCESS("✓ 被依赖次数计算完成"))
    #
    #     except Exception as e:
    #         logger.error(f"被依赖次数计算失败: {str(e)}")
    #         raise

    # -------------------- 课程指标计算 --------------------
    def _calculate_course_metrics(self):
        """计算课程热度和难度"""
        try:
            self.stdout.write("\n[阶段3/5] 正在计算课程指标...")

            # 批量预取数据
            courses = Course.objects.prefetch_related(
                'usercourse_set',
                'concepts'
            ).all()

            # 计算热度和难度
            for course in tqdm(courses, desc="处理课程", unit="courses"):
                # 热度 = 选课人数
                course.popularity = course.usercourse_set.count()

                # 难度 = 关联概念的平均深度
                depths = [c.depth for c in course.concepts.all()]
                course.difficulty = sum(depths) / len(depths) if depths else 1.0

            # 批量更新
            Course.objects.bulk_update(
                courses,
                ['popularity', 'difficulty'],
                batch_size=500
            )
            self.stdout.write(self.style.SUCCESS("✓ 课程指标计算完成"))

        except Exception as e:
            logger.error(f"课程指标计算失败: {str(e)}")
            raise

    # -------------------- 用户学习风格 --------------------
    def _calculate_user_styles(self):
        """分批次计算用户学习风格"""
        try:
            self.stdout.write("\n[阶段4/5] 正在计算用户学习风格...")

            # 分批处理参数
            batch_size = 500  # 根据实际情况调整
            total_users = User.objects.count()

            # 使用迭代器分批次处理
            for offset in range(0, total_users, batch_size):
                users = User.objects.prefetch_related(
                    models.Prefetch(
                        'courses',
                        queryset=Course.objects.prefetch_related(
                            models.Prefetch(
                                'concepts',
                                queryset=Concept.objects.select_related('field')
                            )
                        )
                    )
                ).all()[offset:offset + batch_size]

                for user in tqdm(users, desc=f"处理用户 {offset}-{offset + batch_size}"):
                    field_counter = defaultdict(int)
                    total = 0

                    # 优化课程遍历逻辑
                    for course in user.courses.all():
                        # 直接使用已预取的concepts数据
                        for concept in course.concepts.all():
                            if concept.field:
                                field_counter[concept.field.name] += 1
                                total += 1

                    # 手动序列化为 JSON 字符串，并确保非 ASCII 字符不被转义
                    if total > 0:
                        learning_style_dict = {
                            field: count / total
                            for field, count in field_counter.items()
                        }
                        user.learning_style = json.dumps(learning_style_dict, ensure_ascii=False)
                    else:
                        user.learning_style = json.dumps({}, ensure_ascii=False)

                # 分批提交更新
                User.objects.bulk_update(
                    users,
                    ['learning_style'],
                    batch_size=100  # 进一步减小批量提交量
                )

            self.stdout.write(self.style.SUCCESS("✓ 用户风格计算完成"))

        except Exception as e:
            logger.error(f"用户风格计算失败: {str(e)}")
            raise
    # -------------------- 归一化权重计算 --------------------
    def _calculate_normalized_weights(self):
        """计算课程-概念归一化权重"""
        try:
            self.stdout.write("\n[阶段5/5] 正在计算归一化权重...")

            # 预计算全局参数
            max_depth = Concept.objects.aggregate(
                max=models.Max('depth')
            )['max'] or 1
            max_dep = Concept.objects.aggregate(
                max=models.Max('dependency_count')
            )['max'] or 1

            # 批量处理课程-概念关系
            cc_relations = CourseConcept.objects.select_related(
                'concept', 'course'
            ).all()

            for cc in tqdm(cc_relations, desc="处理关系", unit="relations"):
                # 全局重要性因子（40%）
                global_factor = (
                        0.4 * (cc.concept.dependency_count / max_dep) +
                        0.6 * (1 - cc.concept.depth / max_depth)
                )

                # 课程上下文因子（60%）
                # 视频名称匹配度（30%）
                video_score = sum(
                    1 for name in cc.course.video_name
                    if cc.concept.name in name
                ) / len(cc.course.video_name) if cc.course.video_name else 0

                # 课程内频率（30%）
                course_concepts = cc.course.concepts.count()
                freq_factor = CourseConcept.objects.filter(
                    course=cc.course,
                    concept=cc.concept
                ).count() / course_concepts if course_concepts else 0

                # 综合计算
                cc.normalized_weight = min(
                    0.4 * global_factor +
                    0.3 * video_score +
                    0.3 * freq_factor,
                    1.0
                )

            CourseConcept.objects.bulk_update(
                cc_relations,
                ['normalized_weight'],
                batch_size=1000
            )
            self.stdout.write(self.style.SUCCESS("✓ 归一化权重计算完成"))

        except Exception as e:
            logger.error(f"归一化权重计算失败: {str(e)}")
            raise