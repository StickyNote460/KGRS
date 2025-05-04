# recommender/management/commands/init_features.py
from django.core.management.base import BaseCommand
from recommender.features.pipelines.kg_pipeline import full_kg_feature_pipeline

class Command(BaseCommand):
    help = '初始化特征计算'

    def handle(self, *args, **options):
        full_kg_feature_pipeline.delay()
        self.stdout.write(self.style.SUCCESS('已启动特征计算流水线'))