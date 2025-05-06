from celery import shared_task
from django.conf import settings
from ..calculators import (
    concept_calculators,
    course_calculators
)
import logging

logger = logging.getLogger(__name__)

#支持“增量计算”或“按模块独立调度”
@shared_task(bind=True)
def full_kg_feature_pipeline(self):
    """全量特征计算流水线"""
    try:
        logger.info("开始全量知识图谱特征计算流水线...")

        # 概念特征计算
        logger.info("计算概念深度...")
        concept_calculators.calculate_concept_depth()

        logger.info("计算概念被依赖次数...")
        concept_calculators.calculate_dependency_count()

        logger.info("计算概念熵权TOPSIS分数...")
        concept_calculators.calculate_entropy_topsis()

        # 课程特征计算
        logger.info("计算课程难度...")
        course_calculators.calculate_course_difficulty()

        logger.info("计算课程-概念归一化权重...")
        course_calculators.calculate_normalized_weights()

        logger.info("全量知识图谱特征计算流水线完成")
        return {"status": "success"}

    except Exception as e:
        logger.error(f"知识图谱特征流水线执行失败: {str(e)}")
        raise self.retry(exc=e, countdown=60, max_retries=3)
