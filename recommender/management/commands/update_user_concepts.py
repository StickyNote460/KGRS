# update_user_concepts.py
from django.core.management.base import BaseCommand
from django.db import transaction
from tqdm import tqdm
from recommender.models import User, UserCourse, CourseConcept


class Command(BaseCommand):
    help = 'SQLite优化版用户学习概念更新'

    def add_arguments(self, parser):
        parser.add_argument(
            '--chunk-size',
            type=int,
            default=2000,
            help='用户分块处理数量（默认2000）'
        )
        parser.add_argument(
            '--resume',
            action='store_true',
            help='断点续传模式'
        )

    def handle(self, *args, **kwargs):
        chunk_size = kwargs['chunk_size']
        resume_mode = kwargs['resume']

        # 断点续传：获取已处理用户
        processed_users = set()
        if resume_mode:
            processed_users = set(User.objects.exclude(learned_concepts=[])
                                  .values_list('id', flat=True))
            self.stdout.write(f"断点续传模式，已跳过 {len(processed_users)} 用户")

        # 分块处理用户
        total_users = User.objects.count()
        progress_bar = tqdm(total=total_users, desc="处理进度")

        # 分块获取用户ID
        user_ids = User.objects.order_by('id').values_list('id', flat=True)

        for i in range(0, len(user_ids), chunk_size):
            chunk_ids = user_ids[i:i + chunk_size]

            # 过滤已处理用户
            if resume_mode:
                chunk_ids = [uid for uid in chunk_ids if uid not in processed_users]
                if not chunk_ids:
                    progress_bar.update(len(chunk_ids))
                    continue

            # 批量获取用户课程关系
            user_courses = UserCourse.objects.filter(user_id__in=chunk_ids) \
                .select_related('course')

            # 构建课程ID映射
            course_map = {}
            for uc in user_courses:
                course_map.setdefault(uc.user_id, set()).add(uc.course_id)

            # 批量获取课程概念关系
            course_ids = {cid for cids in course_map.values() for cid in cids}
            course_concepts = CourseConcept.objects.filter(course_id__in=course_ids) \
                .values_list('course_id', 'concept_id')

            # 构建概念映射
            concept_map = {}
            for cid, concept_id in course_concepts:
                concept_map.setdefault(cid, set()).add(concept_id)

            # 准备批量更新数据
            update_users = []
            for user in User.objects.filter(id__in=chunk_ids):
                # 跳过已处理用户
                if resume_mode and user.id in processed_users:
                    continue

                # 计算学习概念
                concepts = set()
                for cid in course_map.get(user.id, []):
                    concepts.update(concept_map.get(cid, []))

                user.learned_concepts = list(concepts)
                update_users.append(user)

            # 批量更新
            if update_users:
                with transaction.atomic():
                    User.objects.bulk_update(update_users, ['learned_concepts'])

                progress_bar.update(len(update_users))

        progress_bar.close()
        self.stdout.write(self.style.SUCCESS("处理完成"))