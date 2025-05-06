# recommender/management/commands/init_features.py
from django.core.management.base import BaseCommand
from recommender.features.pipelines.kg_pipeline import full_kg_feature_pipeline

class Command(BaseCommand):
    help = '初始化特征计算'

    def handle(self, *args, **options):
        full_kg_feature_pipeline.delay()
        self.stdout.write(self.style.SUCCESS('已启动特征计算流水线'))

#####
from django.core.management.base import BaseCommand
from tqdm import tqdm
from recommender.features import (
    calculators as feat_calculators,
    pipelines as feat_pipelines
)


class Command(BaseCommand):
    help = 'Initialize all features'

    def handle(self, *args, **options):
        self.stdout.write("=== 开始初始化特征 ===")

        # 概念特征
        self.stdout.write("\n[阶段1/4] 计算概念特征...")
        feat_calculators.concept_calculators.calculate_concept_depth()
        feat_calculators.concept_calculators.calculate_dependency_count()
        feat_calculators.concept_calculators.calculate_entropy_topsis()

        # 课程特征
        self.stdout.write("\n[阶段2/4] 计算课程特征...")
        feat_calculators.course_calculators.calculate_course_difficulty()
        feat_calculators.course_calculators.calculate_normalized_weights()

        # 用户特征
        self.stdout.write("\n[阶段3/4] 计算用户特征...")
        # 需要将原_user_styles逻辑移到用户特征计算器

        self.stdout.write("\n[阶段4/4] 构建知识图谱...")
        feat_pipelines.kg_pipeline.full_kg_feature_pipeline.delay()

        self.stdout.write("\n=== 特征初始化完成 ===")