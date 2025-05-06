import json
from django.core.management.base import BaseCommand
from recommender.models import User


class Command(BaseCommand):
    help = '导入 user.json 文件中的课程顺序和入学时间到 User 表'

    def handle(self, *args, **kwargs):
        # 读取 JSON 文件
        #json_file_path = 'KGRS/data/raw/user.json'
        json_file_path = 'D:\\Code\\python\\KGRS\\data\\raw\\user.json'

        with open(json_file_path, 'r', encoding='utf-8') as f:
            user_data = json.load(f)

        for data in user_data:
            user_id = data['id']
            course_order = data['course_order']
            enroll_time = data['enroll_time']

            # 查找用户，更新课程顺序和入学时间
            try:
                user = User.objects.get(id=user_id)
                user.learned_courses = course_order  # 更新learned_courses字段
                user.enroll_time = enroll_time  # 更新enroll_time字段
                user.save(update_fields=['learned_courses', 'enroll_time'])

                self.stdout.write(self.style.SUCCESS(f"用户 {user_id} 更新成功"))
            except User.DoesNotExist:
                self.stdout.write(self.style.WARNING(f"用户 {user_id} 未找到"))

