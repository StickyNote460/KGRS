#!/usr/bin/env python
# -*- coding: utf-8 -*-

import os
import django
import logging
import csv
from collections import defaultdict
from django.db import models
from django.core.management import call_command

# Django 环境初始化
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'KGRS.settings')
django.setup()

# 导入模型
from recommender.models import Concept, PrerequisiteDependency

logger = logging.getLogger(__name__)


def calculate_dependency_count():
    """计算概念被依赖次数（作为prerequisite出现的次数）并更新数据库，同时生成CSV文件"""
    try:
        print("\n[开始] 正在计算被依赖次数...")

        # 更高效的统计方式：直接按prerequisite分组计数
        dep_counts = (
            PrerequisiteDependency.objects
            .values('prerequisite')
            .annotate(count=models.Count('prerequisite'))
        )

        # 创建ID到计数的映射
        update_map = {item['prerequisite']: item['count'] for item in dep_counts}

        # 获取所有概念ID（确保没有遗漏）
        all_concept_ids = set(Concept.objects.values_list('id', flat=True))
        processed_ids = set(update_map.keys())

        # 为没有依赖的概念设置默认值0
        for concept_id in all_concept_ids - processed_ids:
            update_map[concept_id] = 0

        # 创建CSV文件
        csv_filename = os.path.join(os.path.dirname(__file__), 'dc.csv')
        with open(csv_filename, mode='w', newline='', encoding='utf-8') as csvfile:
            writer = csv.writer(csvfile)
            writer.writerow(['Concept ID', 'Dependency Count'])

            # 分批更新（避免内存问题）
            batch_size = 1000
            concept_ids = list(update_map.keys())

            for i in range(0, len(concept_ids), batch_size):
                batch = concept_ids[i:i + batch_size]
                concepts = Concept.objects.filter(id__in=batch)

                for concept in concepts:
                    concept.dependency_count = update_map[concept.id]
                    concept.save()  # 使用save()而不是bulk_update，因为这是独立脚本
                    # 写入CSV文件
                    writer.writerow([concept.id, concept.dependency_count])
                    print(f"更新概念ID: {concept.id}, 被依赖次数: {concept.dependency_count}")

        print("[完成] 被依赖次数计算完成")
        print(f"CSV文件已生成: {csv_filename}")

    except Exception as e:
        logger.error(f"被依赖次数计算失败: {str(e)}")
        raise


if __name__ == "__main__":
    calculate_dependency_count()