from django.core.management.base import BaseCommand
from recommender.models import UserCourse, CourseConcept, Concept, User


class Command(BaseCommand):
    help = '通过 UserCourse 和 CourseConcept 导入用户已学习的概念到 User 表'

    def handle(self, *args, **kwargs):
        # 遍历所有用户
        users = User.objects.all()

        for user in users:
            # 获取该用户学习的所有课程
            user_courses = UserCourse.objects.filter(user=user)

            learned_concepts = set()  # 使用集合避免重复概念

            for user_course in user_courses:
                # 获取该课程对应的所有概念
                course_concepts = CourseConcept.objects.filter(course=user_course.course)

                # 添加每个概念的ID到 learned_concepts 中
                for course_concept in course_concepts:
                    learned_concepts.add(course_concept.concept.id)

            # 更新 User 的 learned_concepts 字段
            user.learned_concepts = list(learned_concepts)
            user.save(update_fields=['learned_concepts'])

            self.stdout.write(self.style.SUCCESS(f"用户 {user.id} 的学习概念更新成功"))

