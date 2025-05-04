# recommender/management/commands/calculate_all_fields.py
# 如果出现以下报错，就需要添加前四行导入，Django环境初始化
# django.core.exceptions.ImproperlyConfigured:
# Requested setting INSTALLED_APPS, but settings are not configured.
# You must either define the environment variable DJANGO_SETTINGS_MODULE
# or call settings.configure() before accessing settings.
import os
import django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'KGRS.settings')
django.setup()

import logging
from django.core.management.base import BaseCommand
from django.db import transaction, models
from tqdm import tqdm
import json
from collections import defaultdict
from recommender.models import (
    Concept,
    ParentSonRelation,
    PrerequisiteDependency,
    Course,
    User,
    CourseConcept
)

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = "批量计算并更新所有衍生字段数据"

    def handle(self, *args, **options):
        try:
            with transaction.atomic():
                self._calculate_user_styles()
        except Exception as e:
            logger.error(f"批量计算失败: {str(e)}")
            raise
    # -------------------- 用户学习风格 --------------------
    def _calculate_user_styles(self):
        """分批次计算用户学习风格"""
        try:
            self.stdout.write("\n[阶段4/5] 正在计算用户学习风格...")

            # 分批处理参数
            batch_size = 500  # 根据实际情况调整
            total_users = User.objects.count()

            # 使用迭代器分批次处理
            for offset in range(0, total_users, batch_size):
                users = User.objects.prefetch_related(
                    models.Prefetch(
                        'courses',
                        queryset=Course.objects.prefetch_related(
                            models.Prefetch(
                                'concepts',
                                queryset=Concept.objects.select_related('field')
                            )
                        )
                    )
                ).all()[offset:offset + batch_size]

                for user in tqdm(users, desc=f"处理用户 {offset}-{offset + batch_size}"):
                    field_counter = defaultdict(int)
                    total = 0

                    # 优化课程遍历逻辑
                    for course in user.courses.all():
                        # 直接使用已预取的concepts数据
                        for concept in course.concepts.all():
                            if concept.field:
                                field_counter[concept.field.name] += 1
                                total += 1

                    # 手动序列化为 JSON 字符串，并确保非 ASCII 字符不被转义
                    if total > 0:
                        learning_style_dict = {
                            field: count / total
                            for field, count in field_counter.items()
                        }
                        user.learning_style = json.dumps(learning_style_dict, ensure_ascii=False)
                    else:
                        user.learning_style = json.dumps({}, ensure_ascii=False)

                # 分批提交更新
                User.objects.bulk_update(
                    users,
                    ['learning_style'],
                    batch_size=100  # 进一步减小批量提交量
                )

            self.stdout.write(self.style.SUCCESS("✓ 用户风格计算完成"))

        except Exception as e:
            logger.error(f"用户风格计算失败: {str(e)}")
            raise
