# recommender/kg/build_kg.py
import networkx as nx
import numpy as np
from django.db import transaction
from django.conf import settings
from recommender.models import (
    Concept, Course, PrerequisiteDependency,
    CourseConcept, ParentSonRelation
)
import pickle
import os
import logging

logger = logging.getLogger(__name__)


class KnowledgeGraphBuilder:
    GRAPH_PATH = os.path.join(settings.BASE_DIR, 'data/models/kg_graph.pkl')
    WEIGHT_SCALING_FACTOR = 1000  # 将权重放大到合理范围

    def __init__(self):
        self.graph = nx.DiGraph()
        self.node_mapping = {}
        self._init_normalization_params()

    def _init_normalization_params(self):
        """初始化归一化参数"""
        # 获取所有topsis_score用于归一化
        all_scores = Concept.objects.values_list('topsis_score', flat=True)
        self.min_score = min(all_scores) if all_scores else 0
        self.max_score = max(all_scores) if all_scores else 1e-5

        # 获取所有normalized_weight用于归一化
        all_weights = CourseConcept.objects.values_list('normalized_weight', flat=True)
        self.min_weight = min(all_weights) if all_weights else 0
        self.max_weight = max(all_weights) if all_weights else 1e-5

    def _normalize(self, value, min_val, max_val):
        """Min-Max归一化"""
        if max_val == min_val:
            return 0.5
        return (value - min_val) / (max_val - min_val)

    def _add_concepts(self):
        """批量添加概念节点（优化查询）"""
        concepts = Concept.objects.defer('explanation').iterator()
        for concept in concepts:
            node_id = f"concept:{concept.id}"
            self.node_mapping[node_id] = len(self.node_mapping)
            self.graph.add_node(
                self.node_mapping[node_id],
                type='concept',
                id=concept.id,
                depth=concept.depth,
                topsis_score=concept.topsis_score,
                normalized=self._normalize(concept.topsis_score, self.min_score, self.max_score)
            )

    def _add_courses(self):
        """批量添加课程节点（优化内存）"""
        course_ids = Course.objects.values_list('id', flat=True)
        for cid in course_ids:
            node_id = f"course:{cid}"
            self.node_mapping[node_id] = len(self.node_mapping)
            self.graph.add_node(self.node_mapping[node_id], type='course', id=cid)

    def _add_prerequisite_edges(self):
        """优化后的先修关系边（归一化权重）"""
        deps = PrerequisiteDependency.objects.select_related('prerequisite').values(
            'prerequisite__topsis_score', 'prerequisite__id', 'target__id'
        )

        for dep in deps:
            src_id = f"concept:{dep['prerequisite__id']}"
            dst_id = f"concept:{dep['target__id']}"
            if src_id in self.node_mapping and dst_id in self.node_mapping:
                # 归一化权重计算
                raw_weight = dep['prerequisite__topsis_score']
                norm_weight = self._normalize(raw_weight, self.min_score, self.max_score)
                final_weight = (1 - norm_weight) * self.WEIGHT_SCALING_FACTOR  # 高分概念优先

                self.graph.add_edge(
                    self.node_mapping[src_id],
                    self.node_mapping[dst_id],
                    weight=final_weight,
                    type='prerequisite'
                )

    def _add_course_concept_edges(self):
        """优化后的课程-概念边"""
        relations = CourseConcept.objects.select_related('concept').only(
            'course_id', 'concept_id', 'normalized_weight'
        ).iterator()

        for rel in relations:
            course_id = f"course:{rel.course.id}"
            concept_id = f"concept:{rel.concept.id}"
            if course_id in self.node_mapping and concept_id in self.node_mapping:
                # 归一化权重处理
                norm_weight = self._normalize(
                    rel.normalized_weight,
                    self.min_weight,
                    self.max_weight
                ) * self.WEIGHT_SCALING_FACTOR

                self.graph.add_edge(
                    self.node_mapping[course_id],
                    self.node_mapping[concept_id],
                    weight=norm_weight,
                    type='covers'
                )
                self.graph.add_edge(
                    self.node_mapping[concept_id],
                    self.node_mapping[course_id],
                    weight=norm_weight * 1.5,  # 反向边权重更高
                    type='covered_by'
                )

    def _add_course_prerequisites(self):
        """添加课程间先修关系（使用match_pre_courses）"""
        course_map = {c.name: c.id for c in Course.objects.only('id', 'name')}

        for course in Course.objects.only('id', 'match_pre_courses'):
            src_id = f"course:{course.id}"
            if src_id not in self.node_mapping:
                continue

            for pre_name in course.match_pre_courses:
                pre_id = course_map.get(pre_name)
                if not pre_id:
                    continue

                dst_id = f"course:{pre_id}"
                if dst_id in self.node_mapping:
                    # 设置比概念边更低的权重（优先课程路径）
                    self.graph.add_edge(
                        self.node_mapping[dst_id],
                        self.node_mapping[src_id],
                        weight=0.01 * self.WEIGHT_SCALING_FACTOR,  # 课程路径优先
                        type='course_prerequisite'
                    )

    @transaction.atomic
    def build(self):
        logger.info("Building knowledge graph...")
        self._add_concepts()
        self._add_courses()
        self._add_prerequisite_edges()
        self._add_course_concept_edges()
        self._add_course_prerequisites()

        with open(self.GRAPH_PATH, 'wb') as f:
            pickle.dump((self.graph, self.node_mapping), f)
        logger.info(f"Graph built with {len(self.graph.nodes)} nodes and {len(self.graph.edges)} edges")

    @classmethod
    def load_graph(cls):
        if not os.path.exists(cls.GRAPH_PATH):
            raise FileNotFoundError("Knowledge graph not built yet")
        with open(cls.GRAPH_PATH, 'rb') as f:
            return pickle.load(f)