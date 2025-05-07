# recommender/kg/transE_data.py
import sqlite3
import json
import numpy as np
from collections import defaultdict
from django.conf import settings

RELATION_TYPES = {
    'concept_prerequisite': 0,
    'concept_parent': 1,
    'course_concept': 2,
    'course_prerequisite': 3,
    'user_course': 4
}


class TransEDataLoader:
    def __init__(self):
        db_path = settings.DATABASES['default']['NAME']
        self.conn = sqlite3.connect(db_path)
        self.entity2id = defaultdict(int)
        self.course_name_to_id = {}

    def _load_entities(self):
        entities = []
        # 加载课程
        cursor = self.conn.execute('SELECT id FROM course')
        entities.extend(row[0] for row in cursor)

        # 加载概念
        cursor = self.conn.execute('SELECT id FROM concept')
        entities.extend(row[0] for row in cursor)

        # 加载用户
        cursor = self.conn.execute('SELECT id FROM user')
        entities.extend(row[0] for row in cursor)

        self.entity2id = {e: i for i, e in enumerate(entities)}

    def _generate_triples(self):
        triples = []

        # === 概念先修关系 ===
        cursor = self.conn.execute("SELECT prerequisite_id, target_id FROM prerequisite_dependency")
        triples.extend((h, t, RELATION_TYPES['concept_prerequisite']) for h, t in cursor)

        # === 概念父子关系 ===
        cursor = self.conn.execute("SELECT parent_id, son_id FROM parent_son_relation")
        triples.extend((h, t, RELATION_TYPES['concept_parent']) for h, t in cursor)

        # === 课程-概念关系 ===
        cursor = self.conn.execute("SELECT course_id, concept_id FROM course_concept")
        triples.extend((h, t, RELATION_TYPES['course_concept']) for h, t in cursor)

        # === 课程先修关系 ===
        cursor = self.conn.execute("SELECT id, mpre_courses_id FROM course")
        for course_id, pre_courses_json in cursor:
            try:
                pre_list = json.loads(pre_courses_json) if pre_courses_json else []
                valid_pre_ids = [pre for pre in pre_list if pre in self.entity2id]
                for pre_id in valid_pre_ids:
                    triples.append((pre_id, course_id, RELATION_TYPES['course_prerequisite']))
            except json.JSONDecodeError:
                pass

        # === 用户-课程关系 ===
        cursor = self.conn.execute("SELECT user_id, course_id FROM user_course")
        for user_id, course_id in cursor:
            if user_id in self.entity2id and course_id in self.entity2id:
                triples.append((user_id, course_id, RELATION_TYPES['user_course']))

        return triples

    def save_to_txt(self, output_file='transE_train.txt'):
        self._load_entities()
        triples = self._generate_triples()

        # 最终验证
        max_rel = max(r for h, t, r in triples)
        if max_rel >= len(RELATION_TYPES):
            raise ValueError(f"关系索引越界！检测到最大关系索引 {max_rel}，但只定义了 {len(RELATION_TYPES)} 种关系")

        with open(output_file, 'w') as f:
            for h, t, r in triples:
                f.write(f"{self.entity2id[h]}\t{self.entity2id[t]}\t{r}\n")

        np.save('entity2id.npy', self.entity2id)
        print(f"✅ 成功生成 {len(triples)} 个有效三元组")