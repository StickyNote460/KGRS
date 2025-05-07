import numpy as np
from heapq import heappop, heappush
from django.db import connection
import json
from recommender.kg.transE_data import RELATION_TYPES


class TransEPathFinder:
    def __init__(self):
        self.emb = np.load('entity_emb.npy')
        self.entity2id = np.load('entity2id.npy', allow_pickle=True).item()
        self.id2entity = {v: k for k, v in self.entity2id.items()}

    def _semantic_sim(self, id1, id2):
        return np.dot(self.emb[id1], self.emb[id2]) / (
                np.linalg.norm(self.emb[id1]) * np.linalg.norm(self.emb[id2])
        )

    def _get_course_popularity(self, course_id):
        with connection.cursor() as cursor:
            cursor.execute("SELECT popularity FROM course WHERE id=%s", [course_id])
            return cursor.fetchone()[0]

    def _cold_start_path(self, goal_course_id):
        """冷启动策略：推荐热度最高的前置路径"""
        with connection.cursor() as cursor:
            cursor.execute("""
                WITH RECURSIVE pre_path AS (
                    SELECT id, match_pre_courses, popularity, 0 AS depth
                    FROM course WHERE id = %s
                    UNION ALL
                    SELECT c.id, c.match_pre_courses, c.popularity, depth+1
                    FROM course c, pre_path p
                    WHERE c.id = ANY(p.match_pre_courses)
                )
                SELECT id FROM pre_path ORDER BY popularity DESC LIMIT 5
            """, [goal_course_id])
            return [row[0] for row in cursor.fetchall()]

    def find_path(self, user_id, goal_course_id):
        # 冷启动处理
        if user_id not in self.entity2id:
            return self._cold_start_path(goal_course_id)

        # A*搜索算法
        start = self.entity2id[user_id]
        goal = self.entity2id[goal_course_id]
        heap = [(0, start, [])]
        visited = set()

        while heap:
            cost, current, path = heappop(heap)
            if current == goal:
                return [self.id2entity[n] for n in path + [current]]

            if current in visited: continue
            visited.add(current)

            # 获取邻居节点（需根据实际数据库关系实现）
            neighbors = self._get_neighbors(current)
            for neighbor, rel_type in neighbors:
                weight = 1 - self._semantic_sim(current, neighbor)
                heuristic = 1 - self._semantic_sim(neighbor, goal)
                heappush(heap, (cost + weight + heuristic, neighbor, path + [current]))

        return self._cold_start_path(goal_course_id)  # 降级到冷启动

    def _get_neighbors(self, entity_id):
        """从数据库获取关联实体（示例实现）"""
        entity = self.id2entity[entity_id]
        neighbors = []

        if entity.startswith('user_'):
            # 用户学习过的课程
            with connection.cursor() as cursor:
                cursor.execute("SELECT course_id FROM user_course WHERE user_id=%s", [entity])
                neighbors.extend((self.entity2id[row[0]], RELATION_TYPES['user_course']) for row in cursor)

        elif entity.startswith('course_'):
            # 课程先修关系
            with connection.cursor() as cursor:
                cursor.execute("SELECT match_pre_courses FROM course WHERE id=%s", [entity])
                pre_courses = json.loads(cursor.fetchone()[0] or '[]')
                neighbors.extend((self.entity2id[c], RELATION_TYPES['course_prerequisite']) for c in pre_courses)

        return neighbors