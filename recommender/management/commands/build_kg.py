# recommender/management/commands/build_kg.py
#5.2 20:23
#仅调用接口
from django.core.management.base import BaseCommand
from recommender.kg.build_kg import KnowledgeGraphBuilder

class Command(BaseCommand):
    help = '构建知识图谱'

    def handle(self, *args, **options):
        kg = KnowledgeGraphBuilder()
        kg.build()
        self.stdout.write(self.style.SUCCESS('成功构建知识图谱'))


