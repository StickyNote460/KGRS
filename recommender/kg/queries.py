# recommender/kg/queries.py
from networkx import dijkstra_path
import networkx as nx #5.2 20:14新增


class KGQueryEngine:
    def __init__(self, graph):
        self.graph = graph

    def find_learning_path(self, start_concepts, target_course):
        """寻找最优学习路径"""
        target_concepts = self._get_course_concepts(target_course)
        required = set(target_concepts) - set(start_concepts)

        path = []
        for concept in required:
            try:
                segment = dijkstra_path(
                    self.graph,
                    source=start_concepts[0],
                    target=concept,
                    weight='weight'
                )
                path.extend(segment)
            except nx.NetworkXNoPath:
                continue

        return self._path_to_courses(path)

    def _get_course_concepts(self, course):
        return [f"concept_{c.id}" for c in course.concepts.all()]

    def _path_to_courses(self, path):
        courses = set()
        for node in path:
            if node.startswith('course_'):
                course_id = node.split('_')[1]
                courses.add(course_id)
        return list(courses)