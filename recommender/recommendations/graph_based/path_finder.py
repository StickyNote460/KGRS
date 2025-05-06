# recommender/recommendations/graph_based/path_finder.py
import heapq
import numpy as np
from django.core.cache import cache
from django.db.models import Q
from recommender.kg.build_kg import KnowledgeGraphBuilder
from recommender.models import Course


class PathFinder:
    CACHE_TIMEOUT = 3600 * 6  # 6小时缓存
    COURSE_PRIORITY_BOOST = 0.7  # 课程节点优先系数

    def __init__(self, target_course_id=None):
        self.graph, self.node_mapping = self._load_graph()
        self.reverse_mapping = {v: k for k, v in self.node_mapping.items()}
        self.target_course_id = target_course_id
        self.target_course = self._get_target_course()

    def _load_graph(self):
        cached = cache.get('knowledge_graph')
        if not cached:
            cached = KnowledgeGraphBuilder.load_graph()
            cache.set('knowledge_graph', cached, self.CACHE_TIMEOUT)
        return cached

    def _get_target_course(self):
        if not self.target_course_id:
            return None
        return Course.objects.get(id=self.target_course_id)

    def _heuristic(self, current, target_node):
        """改进的启发式函数"""
        node_data = self.graph.nodes[current]
        target_data = self.graph.nodes[target_node]

        # 基础启发值（深度差异）
        depth_diff = abs(node_data.get('depth', 0) - target_data.get('depth', 0))

        # 类型优先系数
        type_boost = 1.0
        if node_data['type'] == 'course':
            type_boost = self.COURSE_PRIORITY_BOOST

        # 课程先修匹配奖励
        course_boost = 1.0
        if self.target_course and node_data['type'] == 'course':
            if node_data['id'] in self.target_course.match_pre_courses:
                course_boost = 0.5  # 提高匹配先修课的优先级

        return (depth_diff * 0.5 + 1.0) * type_boost * course_boost

    def _get_edge_weight(self, u, v):
        """动态调整边权重"""
        edge_data = self.graph[u][v]
        base_weight = edge_data['weight']

        # 强化课程先修边
        if edge_data['type'] == 'course_prerequisite':
            return base_weight * 0.8

        # 弱化反向边
        if edge_data['type'] == 'covered_by':
            return base_weight * 1.2

        return base_weight

    def find_optimal_path(self, user):
        """优化的路径搜索算法"""
        if not self.target_course:
            raise ValueError("Target course not specified")

        # 初始化起点
        start_nodes = [
                          self.node_mapping[f"concept:{cid}"]
                          for cid in user.learned_concepts
                          if f"concept:{cid}" in self.node_mapping
                      ] + [
                          self.node_mapping[f"course:{cid}"]
                          for cid in user.learned_courses
                          if f"course:{cid}" in self.node_mapping
                      ]

        target_node = self.node_mapping[f"course:{self.target_course.id}"]
        frontier = []
        for node in start_nodes:
            heapq.heappush(frontier, (
                self._heuristic(node, target_node),
                0,  # g_cost
                node,
                []
            ))

        visited = {}
        best_path = None
        min_cost = float('inf')

        while frontier:
            f_cost, g_cost, current, path = heapq.heappop(frontier)

            if current in visited and visited[current] <= g_cost:
                continue
            visited[current] = g_cost

            if current == target_node:
                if g_cost < min_cost:
                    min_cost = g_cost
                    best_path = path + [current]
                continue

            for neighbor in self.graph.neighbors(current):
                edge_weight = self._get_edge_weight(current, neighbor)
                new_g_cost = g_cost + edge_weight
                new_f_cost = new_g_cost + self._heuristic(neighbor, target_node)

                if neighbor not in visited or new_g_cost < visited.get(neighbor, float('inf')):
                    heapq.heappush(frontier, (
                        new_f_cost,
                        new_g_cost,
                        neighbor,
                        path + [current]
                    ))

        return self._post_process(best_path)

    def _post_process(self, path):
        """路径后处理优化"""
        if not path:
            return []

        # 提取课程节点并去重
        #course_ids = []
        course_names = []  # 用于存储课程名称
        seen = set()
        for node in path:
            # 调试输出
            print(f"reverse_mapping[node]: {self.reverse_mapping[node]}")
            # 改为拆分第一个 `:`
            node_type, nid = self.reverse_mapping[node].split(':', 1)
            # node_type, nid = self.reverse_mapping[node].split(':')
            # if node_type == 'course' and nid not in seen:
            #     seen.add(nid)
            #     course_ids.append(nid)
            # 如果是课程节点，获取课程名称
            if node_type == 'course' and nid not in seen:
                seen.add(nid)

                # 获取课程的名称
                try:
                    course = Course.objects.get(id=nid)  # 获取课程对象
                    course_names.append(course.name)  # 添加课程名称
                except Course.DoesNotExist:
                        course_names.append(f"课程 {nid} 不存在")  # 如果课程不存在，则添加默认值
        # 按目标课程的match_pre_courses排序
        if self.target_course and self.target_course.match_pre_courses:
            pre_courses = self.target_course.match_pre_courses
            course_names.sort(
                key=lambda x: pre_courses.index(x) if x in pre_courses else len(pre_courses)
            )

        return course_names

    @classmethod
    def schedule_graph_update(cls):
        """定时更新入口"""
        from recommender.kg.build_kg import KnowledgeGraphBuilder
        KnowledgeGraphBuilder().build()
        cache.delete('knowledge_graph')