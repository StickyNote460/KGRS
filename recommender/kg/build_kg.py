# recommender/kg/build_kg.py
import networkx as nx
import pickle
from django.db import transaction
from ..models import (
    Concept,
    PrerequisiteDependency,
    CourseConcept
)


class KnowledgeGraph:
    def __init__(self):
        self.G = nx.DiGraph()
        self._node_attrs = ['depth', 'normalized_importance']
        self._edge_weights = {
            'prerequisite': 1.0,
            'course_relation': 0.7
        }

    @transaction.atomic
    def build(self):
        """构建知识图谱"""
        self._add_concept_nodes()
        self._add_prerequisite_edges()
        self._add_course_edges()
        return self.G

    def _add_concept_nodes(self):
        """添加概念节点"""
        for concept in Concept.objects.all():
            self.G.add_node(
                f"concept_{concept.id}",
                type='concept',
                depth=concept.depth,
                importance=concept.normalized_importance
            )

    def _add_prerequisite_edges(self):
        """添加先修关系边"""
        for dep in PrerequisiteDependency.objects.select_related('prerequisite', 'target'):
            self.G.add_edge(
                f"concept_{dep.prerequisite_id}",
                f"concept_{dep.target_id}",
                relation='prerequisite',
                weight=self._edge_weights['prerequisite']
            )

    def _add_course_edges(self):
        """添加课程-概念关联边"""
        for cc in CourseConcept.objects.select_related('course', 'concept'):
            self.G.add_edge(
                f"course_{cc.course_id}",
                f"concept_{cc.concept_id}",
                relation='contains',
                weight=cc.normalized_weight
            )
            self.G.add_edge(
                f"concept_{cc.concept_id}",
                f"course_{cc.course_id}",
                relation='belongs_to',
                weight=cc.normalized_weight
            )

    def save_to_disk(self, path='data/models/kg_graph.pkl'):
        with open(path, 'wb') as f:
            pickle.dump(self.G, f)

    @classmethod
    def load_from_disk(cls, path='data/models/kg_graph.pkl'):
        with open(path, 'rb') as f:
            return pickle.load(f)

