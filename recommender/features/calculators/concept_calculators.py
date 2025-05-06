import logging
import numpy as np
import pandas as pd
from collections import defaultdict
from django.db import transaction, models
from tqdm import tqdm
from recommender.models import Concept, ParentSonRelation, PrerequisiteDependency
from recommender.features.utils import EmbeddingCache, WeightOptimizer

logger = logging.getLogger(__name__)


def calculate_concept_depth():
    """计算概念深度（完整实现）"""
    try:
        logger.info("开始计算概念深度...")

        # 重置所有深度
        Concept.objects.update(depth=0)

        # 构建父子关系映射
        children_map = defaultdict(list)
        relations = ParentSonRelation.objects.all().values_list('parent_id', 'son_id')
        for parent_id, son_id in relations:
            children_map[parent_id].append(son_id)

        # 查找根节点
        all_concepts = set(Concept.objects.values_list('id', flat=True))
        has_parent = set(relations.values_list('son_id', flat=True))
        root_ids = list(all_concepts - has_parent)

        # 迭代方式计算深度（避免递归栈溢出）
        processed = set()
        for root_id in tqdm(root_ids, desc="处理根节点"):
            stack = [(root_id, 1)]

            while stack:
                concept_id, current_depth = stack.pop()
                if concept_id in processed:
                    continue

                # 更新深度
                concept = Concept.objects.get(id=concept_id)
                if concept.depth < current_depth:
                    concept.depth = current_depth
                    concept.save(update_fields=['depth'])

                processed.add(concept_id)

                # 处理子节点
                for child_id in children_map.get(concept_id, []):
                    stack.append((child_id, current_depth + 1))

        logger.info(f"完成概念深度计算，处理{len(processed)}个概念")

    except Exception as e:
        logger.error(f"概念深度计算失败: {str(e)}")
        raise


def calculate_dependency_count(batch_size: int = 1000):
    """计算被依赖次数（完整实现）"""
    try:
        logger.info("开始计算被依赖次数...")

        # 分批次处理
        dep_counts = PrerequisiteDependency.objects.values('prerequisite') \
            .annotate(count=models.Count('prerequisite')) \
            .iterator(chunk_size=2000)

        update_dict = {}
        for item in dep_counts:
            update_dict[item['prerequisite']] = item['count']

        # 批量更新
        concept_ids = list(update_dict.keys())
        for i in range(0, len(concept_ids), batch_size):
            batch_ids = concept_ids[i:i + batch_size]
            concepts = Concept.objects.filter(id__in=batch_ids)

            for concept in concepts:
                concept.dependency_count = update_dict.get(concept.id, 0)

            Concept.objects.bulk_update(concepts, ['dependency_count'], batch_size=500)

        # 处理未被依赖的概念
        Concept.objects.exclude(id__in=concept_ids).update(dependency_count=0)

        logger.info("被依赖次数计算完成")

    except Exception as e:
        logger.error(f"被依赖次数计算失败: {str(e)}")
        raise


def calculate_entropy_topsis(smooth_factor: float = 0.1, batch_size: int = 1000):
    """熵权法TOPSIS计算（完整实现）"""
    try:
        logger.info("开始熵权TOPSIS计算...")

        # 获取数据
        queryset = Concept.objects.all().values('id', 'depth', 'dependency_count')
        df = pd.DataFrame.from_records(queryset)

        if df.empty:
            logger.warning("没有找到概念数据")
            return

        # 数据预处理
        matrix = df[['depth', 'dependency_count']].values.astype(float)
        matrix += np.random.normal(0, 1e-12, matrix.shape)  # 添加噪声

        # 处理深度指标（负向指标）
        depth_col = matrix[:, 0]
        non_zero_depth = depth_col[depth_col > 0]
        depth_replace = non_zero_depth.mean() * 0.1 if len(non_zero_depth) > 0 else 1.0
        matrix[:, 0] = 1 / np.where(depth_col == 0, depth_replace, depth_col)

        # 处理被依赖次数指标
        dep_col = matrix[:, 1]
        non_zero_dep = dep_col[dep_col > 0]
        if len(non_zero_dep) / len(dep_col) < 0.01:
            dep_col += 1  # 拉普拉斯平滑
            min_non_zero = non_zero_dep.min() if len(non_zero_dep) > 0 else 1.0
            dep_col = np.where(dep_col == 0, min_non_zero * smooth_factor, dep_col)
            matrix[:, 1] = dep_col

        # 标准化
        norm_matrix = matrix / (np.sqrt(np.sum(matrix ** 2, axis=0)) + 1e-12)

        # 熵权计算
        p = norm_matrix / (np.sum(norm_matrix, axis=0) + 1e-12)
        p = np.clip(p, 1e-12, 1.0)
        entropy = -np.sum(p * np.log(p), axis=0) / np.log(len(df))
        entropy = np.nan_to_num(entropy, nan=1.0)
        weights = (1 - entropy) / (np.sum(1 - entropy) + 1e-12)

        # TOPSIS计算
        weighted_matrix = norm_matrix * weights
        pos_ideal = np.nanmax(weighted_matrix, axis=0)
        neg_ideal = np.nanmin(weighted_matrix, axis=0)

        d_pos = np.sqrt(np.sum((weighted_matrix - pos_ideal) ** 2, axis=1))
        d_neg = np.sqrt(np.sum((weighted_matrix - neg_ideal) ** 2, axis=1))
        topsis_scores = d_neg / (d_pos + d_neg + 1e-12)

        # 数据更新
        concepts = []
        for idx, row in df.iterrows():
            concepts.append(Concept(
                id=row['id'],
                entropy_weight=np.clip(weights[0], 0.0, 1.0),
                topsis_score=np.clip(topsis_scores[idx], 0.0, 1.0)
            ))

        with transaction.atomic():
            Concept.objects.bulk_update(concepts, ['entropy_weight', 'topsis_score'], batch_size=batch_size)

        logger.info("熵权TOPSIS计算完成")

    except Exception as e:
        logger.error(f"熵权TOPSIS计算失败: {str(e)}")
        raise