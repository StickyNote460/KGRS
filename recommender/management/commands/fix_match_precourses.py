# fix_match_precourses.py
from django.core.management.base import BaseCommand
from django.db import transaction
from tqdm import tqdm
from recommender.models import Course


class CourseFixer:
    """课程匹配修复器"""

    def __init__(self):
        self.all_courses = {c.name: c.name for c in Course.objects.all()}
        self.norm_courses = {
            self._normalize(name): name
            for name in self.all_courses
        }

    @staticmethod
    def _normalize(text):
        """标准化文本"""
        return ''.join(filter(str.isalnum, text)).lower()

    def rematch(self, candidate):
        """重新匹配课程"""
        # 直接匹配
        if candidate in self.all_courses:
            return candidate

        # 标准化匹配
        norm_candidate = self._normalize(candidate)
        return self.norm_courses.get(norm_candidate)


class Command(BaseCommand):
    help = '修复match_pre_courses字段（仅保留有效匹配）'

    def add_arguments(self, parser):
        parser.add_argument(
            '--batch-size',
            type=int,
            default=500,
            help='批量处理数量（默认500）'
        )

    def handle(self, *args, **kwargs):
        batch_size = kwargs['batch_size']
        fixer = CourseFixer()

        # 需要处理的课程范围
        queryset = Course.objects.exclude(abstract_pre_courses=[])

        with transaction.atomic():
            updates = []
            for course in tqdm(queryset.iterator(), desc="修复课程"):
                try:
                    # 跳过异常标记
                    if course.abstract_pre_courses == "False":
                        continue

                    # 重新匹配
                    new_matches = []
                    for candidate in course.abstract_pre_courses:
                        if matched := fixer.rematch(candidate):
                            new_matches.append(matched)

                    # 去重处理
                    seen = set()
                    course.match_pre_courses = [
                        x for x in new_matches
                        if not (x in seen or seen.add(x))
                    ]

                    updates.append(course)

                    # 批量提交
                    if len(updates) >= batch_size:
                        self._bulk_update(updates)
                        updates = []

                except Exception as e:
                    self.stderr.write(f"修复失败 {course.id}: {str(e)}")
                    continue

            if updates:
                self._bulk_update(updates)

    def _bulk_update(self, courses):
        """批量更新优化"""
        Course.objects.bulk_update(
            courses,
            ['match_pre_courses'],
            batch_size=500
        )


if __name__ == '__main__':
    import django

    django.setup()
    Command().execute()