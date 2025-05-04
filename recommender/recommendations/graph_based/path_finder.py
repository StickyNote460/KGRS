# recommender/recommendations/graph_based/path_finder.py
from recommender.kg.build_kg import KnowledgeGraph #5.2 20:15新增
from recommender.kg.queries import KGQueryEngine


class LearningPathRecommender:
    def __init__(self, kg_path='data/models/kg_graph.pkl'):
        self.engine = KGQueryEngine(KnowledgeGraph.load_from_disk(kg_path))

    def recommend(self, user, target_course):
        """生成学习路径推荐"""
        mastered = [f"concept_{c.id}" for c in user.get_mastered_concepts()]
        return self.engine.find_learning_path(mastered, target_course)