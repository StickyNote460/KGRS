from django.core.management.base import BaseCommand

from ... import models
from ...models import Concept, Course


class Command(BaseCommand):
    help = 'Initialize metric fields'

    def handle(self, *args, **options):
        # 初始化概念深度
        for concept in Concept.objects.all():
            max_depth = concept.parents.aggregate(models.Max('depth'))['depth__max'] or 0
            concept.depth = max_depth + 1
            concept.save()

        # 初始化课程难度
        for course in Course.objects.all():
            avg_depth = course.concepts.aggregate(models.Avg('depth'))['depth__avg'] or 1.0
            course.difficulty = avg_depth
            course.save()

        self.stdout.write(self.style.SUCCESS('成功初始化所有指标'))